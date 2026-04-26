import os
import json
from typing import Optional, Dict
from dotenv import load_dotenv
from nado_protocol.client import create_nado_client, NadoClientMode
from nado_protocol.utils.math import from_x18, to_x18, round_x18
from nado_protocol.engine_client.types.execute import (
    PlaceMarketOrderParams, MarketOrderParams, PlaceOrderParams, OrderParams,
    CancelOrdersParams, CancelProductOrdersParams
)
from nado_protocol.utils.expiration import OrderType, get_expiration_timestamp
from nado_protocol.utils.order import build_appendix

class Nado:
    """
    A friendly wrapper for the Nado Protocol SDK.
    """
    def __init__(self, private_key: Optional[str] = None, mode: str = "TESTNET"):
        """
        Initialize the Nado client.

        :param private_key: The private key for the account.
        :param mode: The network mode ('TESTNET' or 'MAINNET').
        """
        load_dotenv()
        self._private_key = private_key or os.getenv("NADO_PRIVATE_KEY")
        if not self._private_key:
            raise ValueError("Private key must be provided or set in NADO_PRIVATE_KEY env var.")

        self.mode_str = mode.upper()
        if self.mode_str == "MAINNET":
            self.mode = NadoClientMode.MAINNET
        else:
            self.mode = NadoClientMode.TESTNET

        self.client = create_nado_client(self.mode, self._private_key)
        self._address = self.client.context.signer.address
        self._symbols_cache: Dict[str, int] = {}
        self._id_to_symbol_cache: Dict[int, str] = {}
        self._price_increment_cache: Dict[int, int] = {}
        self._load_symbols()

    def _load_symbols(self):
        """Fetch all products and build symbol mappings and cache increments."""
        # 1. Map symbols to IDs
        symbols_data = self.client.market.get_all_product_symbols()
        for item in symbols_data:
            symbol = item.symbol.upper()
            self._symbols_cache[symbol] = item.product_id
            self._id_to_symbol_cache[item.product_id] = symbol

        # 2. Get market info for increments
        all_products = self.client.market.get_all_engine_markets()
        for spot in all_products.spot_products:
            self._price_increment_cache[spot.product_id] = int(spot.book_info.price_increment_x18)
        for perp in all_products.perp_products:
            self._price_increment_cache[perp.product_id] = int(perp.book_info.price_increment_x18)

    def _resolve_product_id(self, symbol: str) -> int:
        """Map a symbol string to a product ID."""
        symbol = symbol.upper()
        if symbol in self._symbols_cache:
            return self._symbols_cache[symbol]

        # Try appending -PERP if not found
        if f"{symbol}-PERP" in self._symbols_cache:
            return self._symbols_cache[f"{symbol}-PERP"]

        # If it's a digit string, assume it's an ID
        if symbol.isdigit():
            return int(symbol)

        raise ValueError(f"Unknown symbol: {symbol}. Available: {list(self._symbols_cache.keys())}")

    def _parse_error(self, error_str: str) -> tuple[str, Optional[int]]:
        """Attempt to parse error details from a string, which might be JSON."""
        try:
            data = json.loads(error_str)
            return str(data.get("error", error_str)), data.get("error_code")
        except:
            return error_str, None

    def _handle_order_response(self, res, symbol: str) -> dict:
        """Standardize the order response and handle errors."""
        if res.status.value == "success":
            data = {
                "status": "success",
                "symbol": symbol,
            }
            # Only add digest if it exists in the response data
            if res.data and hasattr(res.data, "digest"):
                data["digest"] = res.data.digest
            return data

        error_msg, error_code = self._parse_error(str(res.error))
        return {
            "status": "failure",
            "symbol": symbol,
            "error": error_msg,
            "error_code": error_code or res.error_code
        }

    @property
    def address(self) -> str:
        """Return the default wallet address associated with this client."""
        return self._address

    @property
    def subaccount(self) -> str:
        """Return the default subaccount name."""
        subaccounts = self.client.subaccount.get_subaccounts(address=self._address)
        if not subaccounts.subaccounts:
            raise ValueError("No subaccounts found for this address.")
        return subaccounts.subaccounts[0].subaccount

    @property
    def balance(self) -> float:
        """Return the USDT (Product ID 0) balance."""
        summary = self.client.subaccount.get_engine_subaccount_summary(subaccount=self.subaccount)

        usdt_balance = 0.0
        if summary.spot_balances:
            for balance in summary.spot_balances:
                if balance.product_id == 0:
                    usdt_balance = from_x18(int(balance.balance.amount))
                    break
        return usdt_balance

    def get_position(self, symbol: str) -> dict:
        """
        Get the current position for a specific symbol.

        :param symbol: The symbol (e.g., "BTC", "ETH-PERP")
        :return: A dictionary with amount, v_quote_balance, and average_entry_price.
        """
        product_id = self._resolve_product_id(symbol)
        summary = self.client.subaccount.get_engine_subaccount_summary(subaccount=self.subaccount)

        # Check Spot
        if summary.spot_balances:
            for item in summary.spot_balances:
                if item.product_id == product_id:
                    amount = from_x18(int(item.balance.amount))
                    return {
                        "symbol": symbol,
                        "amount": amount,
                        "v_quote_balance": 0.0,
                        "average_entry_price": 0.0
                    }

        # Check Perp
        if summary.perp_balances:
            for item in summary.perp_balances:
                if item.product_id == product_id:
                    amount = from_x18(int(item.balance.amount))
                    v_quote = from_x18(int(item.balance.v_quote_balance))
                    entry_price = abs(v_quote / amount) if amount != 0 else 0.0
                    return {
                        "symbol": symbol,
                        "amount": amount,
                        "v_quote_balance": v_quote,
                        "average_entry_price": entry_price
                    }

        return {
            "symbol": symbol,
            "amount": 0.0,
            "v_quote_balance": 0.0,
            "average_entry_price": 0.0
        }

    def get_all_positions(self) -> list[dict]:
        """
        Get all non-zero positions.

        :return: A list of dictionaries for all products with a balance.
        """
        summary = self.client.subaccount.get_engine_subaccount_summary(subaccount=self.subaccount)
        positions = []

        # Process Spot
        for item in summary.spot_balances:
            amount = from_x18(int(item.balance.amount))
            if amount != 0:
                symbol = self._id_to_symbol_cache.get(item.product_id, str(item.product_id))
                positions.append({
                    "symbol": symbol,
                    "amount": amount,
                    "v_quote_balance": 0.0,
                    "average_entry_price": 0.0
                })

        # Process Perp
        for item in summary.perp_balances:
            amount = from_x18(int(item.balance.amount))
            if amount != 0:
                symbol = self._id_to_symbol_cache.get(item.product_id, str(item.product_id))
                v_quote = from_x18(int(item.balance.v_quote_balance))
                entry_price = abs(v_quote / amount) if amount != 0 else 0.0
                positions.append({
                    "symbol": symbol,
                    "amount": amount,
                    "v_quote_balance": v_quote,
                    "average_entry_price": entry_price
                })

        return positions

    def get_market_liquidity(self, symbol: str, depth: int = 10) -> dict:
        """
        Get the order book liquidity for a symbol.

        :param symbol: The symbol (e.g., "BTC", "ETH-PERP")
        :param depth: Number of levels to fetch (default 10)
        :return: A dictionary with 'bids' and 'asks' lists of [price, amount].
        """
        product_id = self._resolve_product_id(symbol)
        data = self.client.market.get_market_liquidity(product_id, depth)

        return {
            "bids": [[from_x18(int(b[0])), from_x18(int(b[1]))] for b in data.bids],
            "asks": [[from_x18(int(a[0])), from_x18(int(a[1]))] for a in data.asks]
        }

    def get_price(self, symbol: str) -> float:
        """
        Get the current mid-price for a symbol.

        :param symbol: The symbol (e.g., "BTC", "ETH-PERP")
        :return: Current mid-price (float).
        """
        product_id = self._resolve_product_id(symbol)
        data = self.client.market.get_latest_market_price(product_id)
        bid = from_x18(int(data.bid_x18))
        ask = from_x18(int(data.ask_x18))
        return (bid + ask) / 2.0

    def buy(self, symbol: str, amount: float, slippage: float = 0.05) -> dict:
        """
        Place a market buy order.

        :param symbol: The symbol (e.g., "BTC", "ETH-PERP")
        :param amount: The amount to buy (float)
        :param slippage: Max allowed slippage (default 5%)
        :return: A simplified dictionary with order results.
        """
        try:
            product_id = self._resolve_product_id(symbol)
            params = PlaceMarketOrderParams(
                product_id=product_id,
                market_order=MarketOrderParams(
                    sender=self.subaccount,
                    amount=to_x18(amount),
                    nonce=None
                ),
                slippage=slippage
            )
            res = self.client.market.place_market_order(params)
            return self._handle_order_response(res, symbol)
        except Exception as e:
            msg, code = self._parse_error(str(e))
            return {"status": "failure", "symbol": symbol, "error": msg, "error_code": code}

    def sell(self, symbol: str, amount: float, slippage: float = 0.05) -> dict:
        """
        Place a market sell order.

        :param symbol: The symbol (e.g., "BTC", "ETH-PERP")
        :param amount: The amount to sell (float)
        :param slippage: Max allowed slippage (default 5%)
        :return: A simplified dictionary with order results.
        """
        try:
            product_id = self._resolve_product_id(symbol)
            params = PlaceMarketOrderParams(
                product_id=product_id,
                market_order=MarketOrderParams(
                    sender=self.subaccount,
                    amount=-to_x18(amount),
                    nonce=None
                ),
                slippage=slippage
            )
            res = self.client.market.place_market_order(params)
            return self._handle_order_response(res, symbol)
        except Exception as e:
            msg, code = self._parse_error(str(e))
            return {"status": "failure", "symbol": symbol, "error": msg, "error_code": code}

    def buy_limit(self, symbol: str, price: float, amount: float, expires_in: int = 3600*24, reduce_only: bool = False) -> dict:
        """
        Place a Limit Buy order.

        :param symbol: The symbol (e.g., "BTC", "ETH-PERP")
        :param price: The limit price (float)
        :param amount: The amount to buy (float)
        :param expires_in: Expiration in seconds from now (default 24h)
        :param reduce_only: Whether this is a reduce-only order
        :return: A simplified dictionary with order results.
        """
        try:
            product_id = self._resolve_product_id(symbol)
            price_inc = self._price_increment_cache.get(product_id, 1)

            params = PlaceOrderParams(
                product_id=product_id,
                order=OrderParams(
                    sender=self.subaccount,
                    amount=to_x18(amount),
                    nonce=None,
                    priceX18=round_x18(to_x18(price), price_inc),
                    expiration=get_expiration_timestamp(expires_in),
                    appendix=build_appendix(OrderType.DEFAULT, reduce_only=reduce_only)
                )
            )
            res = self.client.market.place_order(params)
            return self._handle_order_response(res, symbol)
        except Exception as e:
            msg, code = self._parse_error(str(e))
            return {"status": "failure", "symbol": symbol, "error": msg, "error_code": code}

    def sell_limit(self, symbol: str, price: float, amount: float, expires_in: int = 3600*24, reduce_only: bool = False) -> dict:
        """
        Place a Limit Sell order.

        :param symbol: The symbol (e.g., "BTC", "ETH-PERP")
        :param price: The limit price (float)
        :param amount: The amount to sell (float)
        :param expires_in: Expiration in seconds from now (default 24h)
        :param reduce_only: Whether this is a reduce-only order
        :return: A simplified dictionary with order results.
        """
        try:
            product_id = self._resolve_product_id(symbol)
            price_inc = self._price_increment_cache.get(product_id, 1)

            params = PlaceOrderParams(
                product_id=product_id,
                order=OrderParams(
                    sender=self.subaccount,
                    amount=-to_x18(amount),
                    nonce=None,
                    priceX18=round_x18(to_x18(price), price_inc),
                    expiration=get_expiration_timestamp(expires_in),
                    appendix=build_appendix(OrderType.DEFAULT, reduce_only=reduce_only)
                )
            )
            res = self.client.market.place_order(params)
            return self._handle_order_response(res, symbol)
        except Exception as e:
            msg, code = self._parse_error(str(e))
            return {"status": "failure", "symbol": symbol, "error": msg, "error_code": code}

    def cancel_order(self, symbol: str, digest: str) -> dict:
        """
        Cancel a specific order by its digest (order ID).

        :param symbol: The symbol of the product.
        :param digest: The digest (ID) of the order to cancel.
        """
        try:
            product_id = self._resolve_product_id(symbol)
            params = CancelOrdersParams(
                sender=self.subaccount,
                productIds=[product_id],
                digests=[digest],
                nonce=None
            )
            res = self.client.market.cancel_orders(params)
            return self._handle_order_response(res, symbol)
        except Exception as e:
            msg, code = self._parse_error(str(e))
            return {"status": "failure", "symbol": symbol, "error": msg, "error_code": code}

    def cancel_all_orders(self, symbol: Optional[str] = None) -> dict:
        """
        Cancel all open orders for a specific symbol, or for all symbols if None.

        :param symbol: Optional symbol to filter cancellation.
        """
        try:
            if symbol:
                product_ids = [self._resolve_product_id(symbol)]
                display_symbol = symbol
            else:
                # Cancel for all cached products
                product_ids = list(self._id_to_symbol_cache.keys())
                display_symbol = "ALL"

            params = CancelProductOrdersParams(
                sender=self.subaccount,
                productIds=product_ids,
                nonce=None
            )
            res = self.client.market.cancel_product_orders(params)
            return self._handle_order_response(res, display_symbol)
        except Exception as e:
            msg, code = self._parse_error(str(e))
            return {"status": "failure", "symbol": symbol or "ALL", "error": msg, "error_code": code}
