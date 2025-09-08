# Binance USDT-M Futures Testnet Trading Bot

A simple, production-ready Python CLI bot for Binance USDT-M Futures Testnet. Supports Market, Limit, and Stop-Limit orders with robust input validation, logging, and startup health checks.

## Features
- Market, Limit, and Stop-Limit orders (USDT-M Futures)
- Validates symbol filters (step size, tick size, min qty)
- Logs requests, responses, and errors to `bot.log`
- Startup health check: connectivity, server time drift, and credential permissions
- Menu-driven CLI with clear status output

## Requirements
- Python 3.9+
- Binance Futures Testnet API Key/Secret
- Package: `python-binance`

## Quick Start
1) Install dependencies:
```bash
pip install python-binance
```

2) Export your Testnet credentials (recommended):
```bash
export BINANCE_API_KEY=your_testnet_key
export BINANCE_API_SECRET=your_testnet_secret
```

3) Run the bot:
```bash
python /Users/abhayrana/prime/bot.py
```

- The bot points to `https://testnet.binancefuture.com` automatically.
- At startup, a health check runs. If something’s wrong, the bot prints a clear diagnostic and exits.

## Usage
- Choose an order type from the menu.
- Provide a valid USDT-M symbol (e.g., `BTCUSDT`).
- Enter quantity and (if applicable) price values. The bot auto-adjusts to step/tick sizes but will reject values below `minQty`.

Example flow:
```
Select an action:
  1) Place MARKET Order
  2) Place LIMIT Order
  3) Place STOP-LIMIT Order
  4) Exit
Choice (1-4): 1
Symbol (e.g., BTCUSDT): BTCUSDT
Side (BUY/SELL): BUY
Quantity: 0.001
```

The result shows order details (status, orderId, executedQty, etc.). All request/response payloads are saved in `bot.log`.

## Configuration
- API keys: read from `BINANCE_API_KEY` and `BINANCE_API_SECRET` env vars, or you will be prompted.
- Testnet: enforced in code via python-binance Futures URLs.
- Logging: both stdout and `bot.log` in the working directory.

## Troubleshooting
If the bot exits during health check or prints a Binance error, refer to the message shown and the tips below. You can also inspect logs:
```bash
tail -n 100 /Users/abhayrana/prime/bot.log
```

Common issues:
- -2015 Invalid API-key, IP, or permissions
  - Use Futures Testnet keys from the Futures Testnet website
  - Ensure the key has Futures permissions
  - Confirm you’re on `https://testnet.binancefuture.com`

- -1021 Timestamp for this request is outside of the recvWindow
  - Your system clock is off. Enable automatic time sync (macOS: System Settings → Date & Time)

- -2019 Insufficient margin
  - Reduce order size, add Testnet balance, or use lower leverage

- -1111/-1116/-1118 Precision or filter errors
  - Adjust quantity/price to match step size and tick size
  - Try small quantities like `0.001`

- Import warnings in your editor for `binance.*`
  - Install the package in the active interpreter: `pip install python-binance`

## Project Structure
- `bot.py`: Main CLI, `BasicBot` class, logging, validations, order methods, health check
- `bot.log`: Log of requests, responses, and errors (created at runtime)

## Notes
- This bot is for the Binance Futures Testnet only; it is not wired to mainnet.
- Use small quantities on testnet to avoid margin errors.
