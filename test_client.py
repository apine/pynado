import os
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
        bot = Nado(mode="TESTNET")

        print(f"Address: {bot.address}")
        print(f"USDT Balance: {bot.balance}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    test_nado_basic()
