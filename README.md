# Pynado

A friendly, Pythonic wrapper for the [Nado Protocol SDK](https://github.com/nadohq/nado-python-sdk). Pynado simplifies the interaction with the Nado Protocol by abstracting low-level details and handling unit conversions automatically.

## Installation

```bash
pip install pynado
```

## Usage

### 1. Setup

Create a `.env` file in your project root to store your private key securely:

```env
NADO_PRIVATE_KEY='your_private_key_here'
```

### 2. Basic Example

Initialize the client and check your account details:

```python
from pynado import Nado

# Initialize the client (defaults to TESTNET and loads key from .env)
client = Nado()

# Access properties directly
print(f"Wallet Address: {client.address}")
print(f"USDT Balance:   {client.balance:,.2f}")
```

### 3. Trading (Market Orders)

Pynado handles symbol resolution (Spot vs. Perp) and unit scaling (`to_x18`) automatically.

```python
# Market Buy 0.01 BTC (Spot)
client.buy("BTC", 0.01)

# Market Sell 0.5 ETH (Perp)
client.sell("ETH-PERP", 0.5)
```

### 4. Limit Orders

Specify a price and optional expiration (default is 24 hours).

```python
# Limit Buy 0.01 BTC at 65,000 USD
client.buy_limit("BTC", 65000, 0.01)

# Limit Sell 0.1 ETH-PERP at 3,500 USD (Expires in 1 hour, Reduce-Only)
client.sell_limit("ETH-PERP", 3500, 0.1, expires_in=3600, reduce_only=True)
```

### 5. Checking Positions

You can easily check specific positions or get an overview of your entire account.

```python
# Get a specific position
pos = client.get_position("BTC-PERP")
print(f"Amount: {pos['amount']}, Entry Price: {pos['average_entry_price']}")

# Get all active positions
all_pos = client.get_all_positions()
for p in all_pos:
    print(f"{p['symbol']}: {p['amount']}")
```

## Features

*   **Simple Interface:** One class (`Nado`) to rule them all.
*   **Automatic Scaling:** Handles 18-decimal scaling for you (returns `float` for balances, accepts `float` for orders).
*   **Symbol Resolution:** Supports both Spot ("BTC") and Perp ("BTC-PERP") symbols.
*   **Position Management:** Friendly methods to retrieve current holdings and average entry prices.
*   **Intelligent Defaults:** Automatically handles price increments (rounding) and order expiration.
*   **Environment Friendly:** Native support for `.env` files.
