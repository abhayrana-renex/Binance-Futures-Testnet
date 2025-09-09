# Binance USDT-M Futures Testnet Trading Bot

A comprehensive trading bot for Binance USDT-M Futures Testnet with multiple UI interfaces. Supports Market, Limit, Stop-Limit, and Take-Profit Limit orders with robust input validation, logging, startup health checks, and real-time monitoring.

## Features
- **Multiple UI Options**: Web interface, Enhanced CLI, and Original CLI
- **Order Types**: Market, Limit, Stop-Limit, and Take-Profit Limit orders (USDT-M Futures)
- **Real-time Monitoring**: Live account dashboard, price updates, and order tracking
- **Input Validation**: Validates symbol filters (step size, tick size, min qty)
- **Comprehensive Logging**: Logs requests, responses, and errors to `bot.log`
- **Health Checks**: Connectivity, server time drift, and credential permissions
- **Configuration Management**: Easy API key setup and management
- **Responsive Design**: Modern web interface with mobile support

## Requirements
- Python 3.9+
- Binance Futures Testnet API Key/Secret
- Core package: `python-binance`
- Web UI: `Flask`, `Werkzeug`
- Enhanced CLI: `rich`

## Quick Start

### Option 1: Use the Launcher (Recommended)
```bash
python launcher.py
```
The launcher will guide you through choosing your preferred interface and installing any missing dependencies.

### Option 2: Manual Setup
1) Install dependencies:
```bash
pip install -r requirements.txt
```

2) Set your Testnet credentials:
```bash
export BINANCE_API_KEY=your_testnet_key
export BINANCE_API_SECRET=your_testnet_secret
```

3) Choose your interface:

**Web UI (Modern Browser Interface):**
```bash
python web_ui.py
```
Then open http://localhost:5000 in your browser.

**Enhanced CLI (Rich Terminal Interface):**
```bash
python enhanced_cli.py
```

**Original CLI (Simple Text Interface):**
```bash
python bot.py
```

## UI Options

### 🌐 Web UI
- **Modern browser-based interface**
- Real-time dashboard with live updates
- Interactive order placement forms
- Account balance and position monitoring
- Configuration management
- Responsive design for mobile/desktop
- Order history tracking

### 💻 Enhanced CLI
- **Rich terminal interface with colors and formatting**
- Live dashboard with real-time account updates
- Interactive order placement
- Live price monitoring
- Detailed account information
- Progress bars and status indicators

### 🔧 Original CLI
- **Simple text-based interface**
- Basic menu-driven navigation
- Order placement functionality
- Account summary display
- Works without additional dependencies

## Usage

### Web UI Usage
1. Start the web server: `python web_ui.py`
2. Open your browser to `http://localhost:5000`
3. Configure your API keys in the Config section
4. Use the Dashboard to monitor your account
5. Place orders using the Orders page
6. View real-time updates and order history

### Enhanced CLI Usage
1. Start the enhanced CLI: `python enhanced_cli.py`
2. Choose from the interactive menu:
   - Live Dashboard: Real-time account monitoring
   - Place Order: Interactive order placement
   - Price Monitor: Live price tracking
   - Account Details: Detailed account information
   - Health Check: System connectivity test

### Original CLI Usage
1. Start the original CLI: `python bot.py`
2. Choose an action from the menu:
   - 1 Market Order
   - 2 Limit Order
   - 3 Stop-Limit Order
   - 4 Take-Profit Limit Order
   - 5 Account Summary
   - 6 Exit
3. Provide a valid USDT-M symbol (e.g., `BTCUSDT`)
4. Enter quantity and (if applicable) price values

### Order Types
- **Market Orders**: Execute immediately at current market price
- **Limit Orders**: Execute only at specified price or better
- **Stop-Limit Orders**: Trigger when stop price is reached, then place limit order
- **Take-Profit Limit Orders**: Close position at profit target

All orders are validated against exchange filters (step size, tick size, min quantity). Request/response payloads are logged to `bot.log`.

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

- Import warnings in your editor for `binance.*` or `rich.*`
  - Install the packages in the active interpreter: `pip install python-binance rich`

## Project Structure
- `bot.py`: Main CLI, `BasicBot` class, logging, validations, order methods, health check, account summary UI
- `bot.log`: Log of requests, responses, and errors (created at runtime)

## Notes
- This bot is for the Binance Futures Testnet only; it is not wired to mainnet.
- Use small quantities on testnet to avoid margin errors.
