import os
import time
import json
from pynado import Nado
from dotenv import load_dotenv

def test_nado_basic():
    load_dotenv()
    private_key = os.getenv("NADO_PRIVATE_KEY")

    if not private_key:
        print("Error: NADO_PRIVATE_KEY not found in .env file.")
        return

    try:
        print("Initializing Nado client (Testnet)...")
        client = Nado(mode="TESTNET")

        print(f"Address:    {client.address}")
        print(f"Subaccount: {client.subaccount}")
        print(f"Balance:    {client.balance:.2f} USDT")

        symbol = "BTC-PERP"

        # --- Market Data Test ---
        print(f"\n--- Market Data: {symbol} ---")
        price = client.get_price(symbol)
        print(f"Current Mid-Price: {price:.2f}")

        liquidity = client.get_market_liquidity(symbol, depth=1)
        best_bid = liquidity["bids"][0][0] if liquidity["bids"] else 0
        best_ask = liquidity["asks"][0][0] if liquidity["asks"] else 0
        print(f"Best Bid: {best_bid:.2f} | Best Ask: {best_ask:.2f}")

        # --- Complete Trade Cycle ---
        amount = 0.002 # > $100 min notional

        # 1. Place Limit Order
        limit_price = price * 0.9 # 10% below market for safety
        print(f"\n[1/3] Placing Limit BUY at {limit_price:.2f} for {amount} {symbol}...")
        res = client.buy_limit(symbol, limit_price, amount)
        print(f"LIMIT Response: {json.dumps(res, indent=2)}")

        if res["status"] == "success":
            print("\nWaiting 10 seconds before canceling...")
            time.sleep(10)

            digest = res["digest"]
            print(f"\n[2/3] Canceling specific order: {digest}...")
            cancel_res = client.cancel_order(symbol, digest)
            print(f"CANCEL Response: {json.dumps(cancel_res, indent=2)}")

            # 2. Place another and cancel all
            print(f"\n[3/3] Testing cancel_all_orders({symbol})...")
            client.buy_limit(symbol, limit_price, amount)
            all_cancel_res = client.cancel_all_orders(symbol)
            print(f"CANCEL ALL Response: {json.dumps(all_cancel_res, indent=2)}")

        else:
            print(f"Execution failed: {res.get('error', 'Unknown error')}")

    except Exception as e:
        print(f"\nAn unexpected exception occurred: {e}")

if __name__ == "__main__":
    test_nado_basic()
