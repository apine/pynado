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

### 3. Advanced Initialization

You can also pass arguments explicitly if you prefer not to use environment variables or need to switch networks:

```python
client = Nado(private_key="0x...", mode="MAINNET")
```

## Features

*   **Simple Interface:** One class (`Nado`) to rule them all.
*   **Automatic Scaling:** Handles 18-decimal scaling for you (returns `float` for balances).
*   **Environment Friendly:** Native support for `.env` files.
