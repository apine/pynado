import os
from typing import Optional
from dotenv import load_dotenv
from nado_protocol.client import create_nado_client, NadoClientMode
from nado_protocol.utils.math import from_x18, to_x18

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

    @property
    def address(self) -> str:
        """
        Return the default wallet address associated with this client.
        """
        return self._address

    @property
    def balance(self) -> float:
        """
        Return the USDT (Product ID 0) balance.
        """
        # 1. Get Subaccounts
        subaccounts = self.client.subaccount.get_subaccounts(address=self._address)
        if not subaccounts.subaccounts:
            return 0.0

        # We assume the default subaccount (usually "default")
        # In the SDK, subaccount names are often 'default'.
        # The reference code just took the first one.
        first_subaccount = subaccounts.subaccounts[0]
        subaccount_name = first_subaccount.subaccount

        # 2. Get Summary
        summary = self.client.subaccount.get_engine_subaccount_summary(subaccount=subaccount_name)

        # 3. Find USDT balance (Spot Balance with Product ID 0)
        # Assuming 0 is USDT as is standard in Vertex/Nado clones
        usdt_balance = 0.0
        if summary.spot_balances:
            for balance in summary.spot_balances:
                if balance.product_id == 0:
                    usdt_balance = from_x18(int(balance.balance.amount))
                    break

        return usdt_balance
