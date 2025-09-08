import os
import sys
import json
import time
import logging
from decimal import Decimal, ROUND_DOWN
from typing import Any, Dict, Optional, Tuple

from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException
from binance.enums import (
    SIDE_BUY,
    SIDE_SELL,
    ORDER_TYPE_MARKET,
    ORDER_TYPE_LIMIT,
    TIME_IN_FORCE_GTC,
)


LOG_FILE = "bot.log"

# Optional Rich TUI
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box
    RICH_AVAILABLE = True
    _RICH_CONSOLE: Optional[Console] = Console()
except Exception:
    RICH_AVAILABLE = False
    _RICH_CONSOLE = None


def setup_logger(level: int = logging.INFO) -> logging.Logger:
    """Configure module-level logger writing to bot.log and stdout."""
    logger = logging.getLogger("BasicBot")
    logger.setLevel(level)
    logger.propagate = False

    if not logger.handlers:
        # File handler to persist all bot activity
        file_handler = logging.FileHandler(LOG_FILE)
        file_handler.setLevel(level)
        file_formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        # Stream handler for concise CLI visibility
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(level)
        stream_formatter = logging.Formatter("%(message)s")
        stream_handler.setFormatter(stream_formatter)
        logger.addHandler(stream_handler)

    return logger


class BasicBot:
    """
    Basic trading bot for Binance USDT-M Futures Testnet.

    - Supports market, limit, and stop-limit orders
    - Validates and formats quantities/prices per exchange filters
    - Logs all requests, responses, and errors
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        testnet: bool = True,
        log_level: int = logging.INFO,
    ) -> None:
        self.logger = setup_logger(log_level)
        self.testnet = testnet

        # Point python-binance Futures endpoints to Testnet if requested
        if self.testnet:
            # python-binance uses these attributes for futures base urls
            # Override to route all futures requests to testnet
            Client.FUTURES_URL = "https://testnet.binancefuture.com/fapi"
            Client.FUTURES_DATA_URL = "https://testnet.binancefuture.com/fapi"
            # Some installs reference FUTURES_URL_V2; keep consistent
            if hasattr(Client, "FUTURES_URL_V2"):
                Client.FUTURES_URL_V2 = "https://testnet.binancefuture.com/fapi"

        self.client = Client(api_key, api_secret)

        # Cache exchange info for validations and formatting
        self._exchange_info_cache: Dict[str, Dict[str, Any]] = {}

    # ---------- Utility Methods ----------
    def _log_request(self, operation: str, params: Dict[str, Any]) -> None:
        self.logger.info("REQUEST | %s | %s", operation, json.dumps(params, default=str))

    def _log_response(self, operation: str, response: Dict[str, Any]) -> None:
        self.logger.info("RESPONSE | %s | %s", operation, json.dumps(response, default=str))

    def _log_error(self, operation: str, exc: Exception) -> None:
        self.logger.error("ERROR | %s | %s: %s", operation, type(exc).__name__, str(exc))

    def _get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """Fetch and cache futures symbol info for validations and formatting."""
        symbol = symbol.upper()
        if symbol in self._exchange_info_cache:
            return self._exchange_info_cache[symbol]

        info = self.client.futures_exchange_info()
        symbols = info.get("symbols", [])
        for s in symbols:
            if s.get("symbol") == symbol:
                self._exchange_info_cache[symbol] = s
                return s
        raise ValueError(f"Symbol not found in Futures exchange info: {symbol}")

    @staticmethod
    def _to_decimal(value: Any) -> Decimal:
        return Decimal(str(value))

    @staticmethod
    def _round_step(value: Decimal, step: Decimal) -> Decimal:
        """Round value down to valid step using exchange filter step size."""
        if step == 0:
            return value
        quant = (value / step).to_integral_value(rounding=ROUND_DOWN)
        return (quant * step).quantize(step)

    def _apply_filters(
        self,
        symbol: str,
        quantity: Optional[Decimal] = None,
        price: Optional[Decimal] = None,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Apply LOT_SIZE/MARKET_LOT_SIZE and PRICE_FILTER to given quantity/price.
        Returns tuple of (quantity_str, price_str) with proper precision.
        """
        info = self._get_symbol_info(symbol)
        lot_step = None
        min_qty = None
        price_tick = None

        for f in info.get("filters", []):
            if f.get("filterType") in ("LOT_SIZE", "MARKET_LOT_SIZE"):
                lot_step = self._to_decimal(f.get("stepSize", "0"))
                min_qty = self._to_decimal(f.get("minQty", "0"))
            elif f.get("filterType") == "PRICE_FILTER":
                price_tick = self._to_decimal(f.get("tickSize", "0"))

        qty_str = None
        price_str = None

        if quantity is not None:
            if lot_step is None or min_qty is None:
                raise ValueError("Exchange filters missing LOT_SIZE/MARKET_LOT_SIZE")
            if quantity <= 0:
                raise ValueError("Quantity must be positive")
            adj_qty = self._round_step(quantity, lot_step)
            if adj_qty < min_qty:
                raise ValueError(f"Quantity {quantity} below min {min_qty}")
            # Format with normalized string (strip trailing zeros)
            qty_str = format(adj_qty.normalize(), 'f')

        if price is not None:
            if price_tick is None:
                raise ValueError("Exchange filters missing PRICE_FILTER")
            if price <= 0:
                raise ValueError("Price must be positive")
            adj_price = self._round_step(price, price_tick)
            price_str = format(adj_price.normalize(), 'f')

        return qty_str, price_str

    # ---------- Public Order Methods ----------
    def health_check(self) -> None:
        """
        Connectivity and time-sync checks. Logs and raises if unreachable.
        Also checks credential validity by calling futures account endpoint.
        """
        operation = "health_check"
        try:
            self._log_request(operation, {"action": "ping"})
            self.client.futures_ping()
            self._log_response(operation, {"ping": "ok"})

            self._log_request(operation, {"action": "time"})
            server_time = self.client.futures_time()
            self._log_response(operation, server_time)
            server_ms = int(server_time.get("serverTime", 0))
            local_ms = int(time.time() * 1000)
            drift_ms = abs(server_ms - local_ms)
            if drift_ms > 2000:
                self.logger.warning(
                    "Clock drift detected (~%sms). Enable automatic time sync on your OS.",
                    drift_ms,
                )

            # Credential/permission check
            self._log_request(operation, {"action": "account"})
            acct = self.client.futures_account()
            self._log_response(operation, {"canTrade": acct.get("canTrade", None)})
        except (BinanceAPIException, BinanceOrderException, Exception) as exc:
            self._log_error(operation, exc)
            raise

    @staticmethod
    def explain_binance_error(exc: Exception) -> Optional[str]:
        """Return a human-friendly diagnostic for common Binance errors."""
        code = getattr(exc, "code", None)
        msg = str(getattr(exc, "message", str(exc)))

        hints = {
            -2015: (
                "Invalid API-key, IP, or permissions. Use Futures Testnet keys, enable Futures, "
                "and ensure you're pointing to https://testnet.binancefuture.com."
            ),
            -2014: (
                "API-key format or permissions issue. Regenerate Testnet keys and reconfigure."
            ),
            -1021: (
                "Timestamp for this request is outside of the recvWindow. Sync your system clock "
                "(enable automatic time) and retry."
            ),
            -2019: (
                "Insufficient margin. Reduce order size or add Testnet balance; consider lower leverage."
            ),
            -1111: (
                "Precision error. Quantity/price not matching step size/tick size. Try smaller qty or valid price."
            ),
            -1116: (
                "Invalid order type/side/symbol. Ensure USDT-M symbol like BTCUSDT and supported order type."
            ),
            -1118: (
                "Order rejected due to filter. Value out of bounds (minQty, stepSize, tickSize)."
            ),
        }
        if isinstance(code, int) and code in hints:
            return f"{code}: {hints[code]} (Details: {msg})"
        # Generic message fallback
        if code is not None:
            return f"{code}: {msg}"
        return None

    def place_market_order(self, symbol: str, side: str, quantity: Any) -> Dict[str, Any]:
        """Place a USDT-M Futures market order."""
        operation = "futures_create_order_market"
        symbol = symbol.upper()
        side = side.upper()
        raw_qty = self._to_decimal(quantity)

        qty_str, _ = self._apply_filters(symbol, quantity=raw_qty, price=None)
        params = {
            "symbol": symbol,
            "side": side,
            "type": ORDER_TYPE_MARKET,
            "quantity": qty_str,
        }
        self._log_request(operation, params)
        try:
            resp = self.client.futures_create_order(**params)
            self._log_response(operation, resp)
            return resp
        except (BinanceAPIException, BinanceOrderException, Exception) as exc:
            self._log_error(operation, exc)
            raise

    def place_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: Any,
        price: Any,
        time_in_force: str = TIME_IN_FORCE_GTC,
    ) -> Dict[str, Any]:
        """Place a USDT-M Futures limit order."""
        operation = "futures_create_order_limit"
        symbol = symbol.upper()
        side = side.upper()
        raw_qty = self._to_decimal(quantity)
        raw_price = self._to_decimal(price)

        qty_str, price_str = self._apply_filters(symbol, quantity=raw_qty, price=raw_price)
        params = {
            "symbol": symbol,
            "side": side,
            "type": ORDER_TYPE_LIMIT,
            "timeInForce": time_in_force,
            "quantity": qty_str,
            "price": price_str,
        }
        self._log_request(operation, params)
        try:
            resp = self.client.futures_create_order(**params)
            self._log_response(operation, resp)
            return resp
        except (BinanceAPIException, BinanceOrderException, Exception) as exc:
            self._log_error(operation, exc)
            raise

    def place_stop_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: Any,
        stop_price: Any,
        limit_price: Any,
        time_in_force: str = TIME_IN_FORCE_GTC,
    ) -> Dict[str, Any]:
        """
        Place a USDT-M Futures stop-limit order.
        Futures API uses type "STOP" with stopPrice and price.
        """
        operation = "futures_create_order_stop_limit"
        symbol = symbol.upper()
        side = side.upper()
        raw_qty = self._to_decimal(quantity)
        raw_stop = self._to_decimal(stop_price)
        raw_limit = self._to_decimal(limit_price)

        qty_str, limit_str = self._apply_filters(symbol, quantity=raw_qty, price=raw_limit)
        # stopPrice follows tick size as well; apply same price filter
        _, stop_str = self._apply_filters(symbol, quantity=None, price=raw_stop)

        params = {
            "symbol": symbol,
            "side": side,
            "type": "STOP",
            "timeInForce": time_in_force,
            "quantity": qty_str,
            "price": limit_str,
            "stopPrice": stop_str,
        }
        self._log_request(operation, params)
        try:
            resp = self.client.futures_create_order(**params)
            self._log_response(operation, resp)
            return resp
        except (BinanceAPIException, BinanceOrderException, Exception) as exc:
            self._log_error(operation, exc)
            raise

    def place_take_profit_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: Any,
        stop_price: Any,
        limit_price: Any,
        time_in_force: str = TIME_IN_FORCE_GTC,
    ) -> Dict[str, Any]:
        """
        Place a USDT-M Futures take-profit limit order.
        Futures API uses type "TAKE_PROFIT" with stopPrice and price.
        """
        operation = "futures_create_order_tp_limit"
        symbol = symbol.upper()
        side = side.upper()
        raw_qty = self._to_decimal(quantity)
        raw_stop = self._to_decimal(stop_price)
        raw_limit = self._to_decimal(limit_price)

        qty_str, limit_str = self._apply_filters(symbol, quantity=raw_qty, price=raw_limit)
        _, stop_str = self._apply_filters(symbol, quantity=None, price=raw_stop)

        params = {
            "symbol": symbol,
            "side": side,
            "type": "TAKE_PROFIT",
            "timeInForce": time_in_force,
            "quantity": qty_str,
            "price": limit_str,
            "stopPrice": stop_str,
        }
        self._log_request(operation, params)
        try:
            resp = self.client.futures_create_order(**params)
            self._log_response(operation, resp)
            return resp
        except (BinanceAPIException, BinanceOrderException, Exception) as exc:
            self._log_error(operation, exc)
            raise

    def get_account_summary(self) -> Dict[str, Any]:
        """Return a concise futures account summary: balances and open positions."""
        operation = "account_summary"
        summary: Dict[str, Any] = {"balances": [], "positions": []}
        try:
            self._log_request(operation, {"action": "balances"})
            balances = self.client.futures_account_balance()
            self._log_response(operation, {"balances_count": len(balances)})
            for b in balances:
                if b.get("asset") == "USDT":
                    summary["balances"].append(
                        {
                            "asset": b.get("asset"),
                            "balance": b.get("balance"),
                            "availableBalance": b.get("availableBalance"),
                        }
                    )

            self._log_request(operation, {"action": "positions"})
            positions = self.client.futures_position_information()
            self._log_response(operation, {"positions_count": len(positions)})
            for p in positions:
                pos_amt = Decimal(p.get("positionAmt", "0"))
                if pos_amt != 0:
                    summary["positions"].append(
                        {
                            "symbol": p.get("symbol"),
                            "positionAmt": p.get("positionAmt"),
                            "entryPrice": p.get("entryPrice"),
                            "unRealizedProfit": p.get("unRealizedProfit"),
                            "leverage": p.get("leverage"),
                            "marginType": p.get("marginType"),
                        }
                    )
        except (BinanceAPIException, BinanceOrderException, Exception) as exc:
            self._log_error(operation, exc)
            raise
        return summary


def _prompt_non_empty(prompt: str) -> str:
    while True:
        val = input(prompt).strip()
        if val:
            return val
        print("Input cannot be empty. Please try again.")


def _prompt_choice(prompt: str, choices: Tuple[str, ...]) -> str:
    choices_upper = tuple(c.upper() for c in choices)
    while True:
        val = input(prompt).strip().upper()
        if val in choices_upper:
            return val
        print(f"Invalid choice. Options: {', '.join(choices_upper)}")


def _prompt_decimal(prompt: str) -> Decimal:
    while True:
        raw = input(prompt).strip()
        try:
            value = Decimal(raw)
            if value <= 0:
                raise ValueError
            return value
        except Exception:
            print("Please enter a positive number.")


def print_order_result(title: str, data: Dict[str, Any]) -> None:
    """Render a concise order result to the CLI."""
    fields = [
        ("symbol", data.get("symbol")),
        ("side", data.get("side")),
        ("type", data.get("type")),
        ("status", data.get("status")),
        ("orderId", data.get("orderId")),
        ("clientOrderId", data.get("clientOrderId")),
        ("origQty", data.get("origQty")),
        ("executedQty", data.get("executedQty")),
        ("price", data.get("price")),
        ("avgPrice", data.get("avgPrice")),
        ("stopPrice", data.get("stopPrice")),
        ("updateTime", data.get("updateTime")),
    ]
    if RICH_AVAILABLE and _RICH_CONSOLE:
        table = Table(title=title, box=box.SIMPLE_HEAVY)
        table.add_column("Field", style="cyan", no_wrap=True)
        table.add_column("Value", style="white")
        for key, value in fields:
            if value is not None:
                table.add_row(str(key), str(value))
        _RICH_CONSOLE.print(table)
    else:
        print("\n" + title)
        print("-" * len(title))
        for key, value in fields:
            if value is not None:
                print(f"{key}: {value}")
        print()


def print_account_summary(summary: Dict[str, Any]) -> None:
    if RICH_AVAILABLE and _RICH_CONSOLE:
        header = Panel.fit("[bold green]Account Summary[/bold green]", border_style="green")
        _RICH_CONSOLE.print(header)

        bal_table = Table(title="Balances", box=box.SIMPLE_HEAVY)
        bal_table.add_column("Asset", style="cyan")
        bal_table.add_column("Total", style="white")
        bal_table.add_column("Available", style="white")
        if summary.get("balances"):
            for b in summary["balances"]:
                bal_table.add_row(
                    str(b.get("asset")), str(b.get("balance")), str(b.get("availableBalance"))
                )
        else:
            bal_table.add_row("-", "-", "-")
        _RICH_CONSOLE.print(bal_table)

        pos_table = Table(title="Open Positions", box=box.SIMPLE_HEAVY)
        pos_table.add_column("Symbol", style="cyan")
        pos_table.add_column("Amt", style="white")
        pos_table.add_column("Entry", style="white")
        pos_table.add_column("uPnL", style="white")
        pos_table.add_column("Lev", style="white")
        pos_table.add_column("Margin", style="white")
        if summary.get("positions"):
            for p in summary["positions"]:
                pos_table.add_row(
                    str(p.get("symbol")),
                    str(p.get("positionAmt")),
                    str(p.get("entryPrice")),
                    str(p.get("unRealizedProfit")),
                    str(p.get("leverage")),
                    str(p.get("marginType")),
                )
        else:
            pos_table.add_row("-", "-", "-", "-", "-", "-")
        _RICH_CONSOLE.print(pos_table)
    else:
        print("\nAccount Summary")
        print("---------------")
        if summary.get("balances"):
            for b in summary["balances"]:
                print(
                    f"Balance {b.get('asset')}: total={b.get('balance')} available={b.get('availableBalance')}"
                )
        else:
            print("No balances returned.")

        if summary.get("positions"):
            print("\nOpen Positions:")
            for p in summary["positions"]:
                print(
                    f"{p.get('symbol')} amt={p.get('positionAmt')} entry={p.get('entryPrice')} "
                    f"uPnL={p.get('unRealizedProfit')} lev={p.get('leverage')} margin={p.get('marginType')}"
                )
        else:
            print("\nNo open positions.")
        print()

def main() -> None:
    logger = setup_logger()

    # API credentials: prefer environment variables, fallback to prompts
    api_key = os.getenv("BINANCE_API_KEY") or _prompt_non_empty("Enter API Key: ")
    api_secret = os.getenv("BINANCE_API_SECRET") or _prompt_non_empty("Enter API Secret: ")

    # Initialize bot (defaults to testnet)
    bot = BasicBot(api_key=api_key, api_secret=api_secret, testnet=True, log_level=logging.INFO)

    if RICH_AVAILABLE and _RICH_CONSOLE:
        _RICH_CONSOLE.print(Panel.fit("[bold]Binance Futures Testnet Trading Bot[/bold]\nhttps://testnet.binancefuture.com", border_style="blue"))
    else:
        print("\nBinance Futures Testnet Trading Bot")
        print("===================================")
        print("Connected to: https://testnet.binancefuture.com")

    # Startup health check: connectivity, time sync, and credentials
    try:
        bot.health_check()
        print("Health check: OK (network, time, credentials)")
    except (BinanceAPIException, BinanceOrderException) as be:
        diag = BasicBot.explain_binance_error(be)
        print("Health check failed: Binance error")
        if diag:
            print(diag)
        else:
            print(str(be))
        return
    except Exception as exc:
        logger.exception("Startup health check failed")
        print(f"Health check failed: {exc}")
        return

    # Simple interactive menu
    while True:
        if RICH_AVAILABLE and _RICH_CONSOLE:
            menu = (
                "[bold]Select an action:[/bold]\n"
                "  [cyan]1[/cyan]) Place MARKET Order\n"
                "  [cyan]2[/cyan]) Place LIMIT Order\n"
                "  [cyan]3[/cyan]) Place STOP-LIMIT Order\n"
                "  [cyan]4[/cyan]) Place TAKE-PROFIT LIMIT Order\n"
                "  [cyan]5[/cyan]) View Account Summary\n"
                "  [cyan]6[/cyan]) Exit"
            )
            _RICH_CONSOLE.print(Panel(menu, border_style="magenta"))
        else:
            print("\nSelect an action:")
            print("  1) Place MARKET Order")
            print("  2) Place LIMIT Order")
            print("  3) Place STOP-LIMIT Order")
            print("  4) Place TAKE-PROFIT LIMIT Order")
            print("  5) View Account Summary")
            print("  6) Exit")

        choice = _prompt_choice("Choice (1-6): ", ("1", "2", "3", "4", "5", "6"))
        if choice == "6":
            print("Goodbye!")
            break

        symbol = _prompt_non_empty("Symbol (e.g., BTCUSDT): ").upper()
        if not symbol.endswith("USDT"):
            print("Only USDT-M Futures symbols are supported (e.g., BTCUSDT).")
            continue

        side = _prompt_choice("Side (BUY/SELL): ", ("BUY", "SELL"))

        try:
            if choice == "1":
                qty = _prompt_decimal("Quantity: ")
                result = bot.place_market_order(symbol=symbol, side=side, quantity=qty)
                print_order_result("Market Order Result", result)

            elif choice == "2":
                qty = _prompt_decimal("Quantity: ")
                price = _prompt_decimal("Limit Price: ")
                result = bot.place_limit_order(symbol=symbol, side=side, quantity=qty, price=price)
                print_order_result("Limit Order Result", result)

            elif choice == "3":
                qty = _prompt_decimal("Quantity: ")
                stop_price = _prompt_decimal("Stop Price (trigger): ")
                limit_price = _prompt_decimal("Limit Price (after trigger): ")
                result = bot.place_stop_limit_order(
                    symbol=symbol,
                    side=side,
                    quantity=qty,
                    stop_price=stop_price,
                    limit_price=limit_price,
                )
                print_order_result("Stop-Limit Order Result", result)

            elif choice == "4":
                qty = _prompt_decimal("Quantity: ")
                stop_price = _prompt_decimal("Stop Price (trigger): ")
                limit_price = _prompt_decimal("Limit Price (after trigger): ")
                result = bot.place_take_profit_limit_order(
                    symbol=symbol,
                    side=side,
                    quantity=qty,
                    stop_price=stop_price,
                    limit_price=limit_price,
                )
                print_order_result("Take-Profit Limit Order Result", result)

            elif choice == "5":
                summary = bot.get_account_summary()
                print_account_summary(summary)

        except ValueError as ve:
            logger.error("Validation error: %s", str(ve))
            print(f"Validation error: {ve}")
        except (BinanceAPIException, BinanceOrderException) as be:
            logger.error("Binance error: %s", str(be))
            diag = BasicBot.explain_binance_error(be)
            if diag:
                print(f"Binance error: {diag}")
            else:
                print(f"Binance error: {be}")
        except Exception as exc:
            logger.exception("Unexpected error")
            print(f"Unexpected error: {exc}")
        finally:
            # Small pause to keep outputs tidy
            time.sleep(0.5)


if __name__ == "__main__":
    main()


