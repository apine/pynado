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

        print(f"\n[1/2] Placing Market BUY for {amount} {symbol}...")
        buy_res = client.buy(symbol, amount)
        print(f"BUY Response: {json.dumps(buy_res, indent=2)}")

        if buy_res["status"] == "success":
            print("\nWaiting 2 seconds for engine to settle...")
            time.sleep(2)

            pos = client.get_position(symbol)
            print(f"Current Position: {json.dumps(pos, indent=2)}")

            print("\nWaiting 10 seconds before selling...")
            time.sleep(10)

            print(f"[2/2] Placing Market SELL for {amount} {symbol}...")
            sell_res = client.sell(symbol, amount)
            print(f"SELL Response: {json.dumps(sell_res, indent=2)}")

            print("\nFinal Position Check:")
            final_pos = client.get_position(symbol)
            print(json.dumps(final_pos, indent=2))
        else:
            print("Skipping further steps because buy failed.")

    except Exception as e:
        print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    test_nado_basic()
