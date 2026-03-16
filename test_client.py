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
        amount = 0.002 # > $100 min notional

        # 1. Place Limit Order
        limit_price = 50000.0 # Way out of money for safety
        print(f"\n[1/3] Placing Limit BUY at {limit_price} for {amount} {symbol}...")
        res = client.buy_limit(symbol, limit_price, amount)
        print(f"LIMIT Response: {json.dumps(res, indent=2)}")

        if res["status"] == "success":
            print("\nWaiting 10 seconds before canceling...")
            time.sleep(10)

            digest = res["digest"]
            print(f"\n[2/3] Canceling specific order: {digest}...")
            cancel_res = client.cancel_order(symbol, digest)
            print(f"CANCEL Response: {json.dumps(cancel_res, indent=2)}")
            print("\nWaiting 5 seconds before next test")
            time.sleep(5)

            # 2. Place another and cancel all
            print(f"\n[3/3] Placing another order and testing cancel_all_orders()...")
            client.buy_limit(symbol, limit_price, amount)
            print("\nWaiting 10 seconds before canceling...")
            time.sleep(10)
            all_cancel_res = client.cancel_all_orders(symbol)
            print(f"CANCEL ALL Response: {json.dumps(all_cancel_res, indent=2)}")

        else:
            print(f"Execution failed: {res.get('error', 'Unknown error')}")

    except Exception as e:
        print(f"\nAn unexpected exception occurred: {e}")

if __name__ == "__main__":
    test_nado_basic()
