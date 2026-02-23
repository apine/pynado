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

        # --- Complete Trade Cycle ---
        symbol = "BTC-PERP"
        amount = 0.0001 # Small test amount

        # 1. Market Buy
        print(f"\n[1/3] Placing Market BUY for {amount} {symbol}...")
        buy_res = client.buy(symbol, amount)
        print(f"BUY Response: {json.dumps(buy_res, indent=2)}")

        if buy_res["status"] == "success":
            time.sleep(2)
            pos = client.get_position(symbol)
            print(f"Current Position: {json.dumps(pos, indent=2)}")

            # 2. Limit Sell (Closing)
            limit_price = pos["average_entry_price"] * 1.05 # 5% profit target
            print(f"\n[2/3] Placing Limit SELL at {limit_price:.2f} for {amount} {symbol}...")
            limit_res = client.sell_limit(symbol, limit_price, amount, expires_in=60, reduce_only=True)
            print(f"LIMIT Response: {json.dumps(limit_res, indent=2)}")

            # 3. Cleanup: Market Sell to actually close
            print(f"\n[3/3] Closing position with Market SELL...")
            sell_res = client.sell(symbol, amount)
            print(f"SELL Response: {json.dumps(sell_res, indent=2)}")

        else:
            print("Skipping further steps because buy failed.")

    except Exception as e:
        print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    test_nado_basic()
