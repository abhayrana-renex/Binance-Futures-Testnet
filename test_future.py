# test_futures_key.py
import os
from binance.client import Client

api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_API_SECRET")

if not api_key or not api_secret:
    print("Set BINANCE_API_KEY and BINANCE_API_SECRET in this terminal.")
    raise SystemExit(1)

# create client (testnet=True) and force futures endpoint
client = Client(api_key, api_secret, testnet=True)
client.FUTURES_URL = "https://testnet.binancefuture.com/fapi"

try:
    # public futures endpoint to check connectivity
    info = client.futures_exchange_info()
    print("Futures exchange info fetched OK.")
except Exception as e:
    print("Futures exchange_info failed:", e)

try:
    # private futures endpoint — will check if key works/has permissions
    bal = client.futures_account_balance()
    print("Futures account balance OK. Sample output (truncated):")
    print(bal[:3])
except Exception as e:
    print("Futures account balance failed (key might be wrong type or missing permissions):", e)