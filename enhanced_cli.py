#!/usr/bin/env python3
"""
Enhanced CLI Interface for Binance Futures Trading Bot

An improved command-line interface with:
- Real-time account monitoring
- Better formatting and colors
- Interactive order placement
- Live price updates
- Configuration management
"""

import os
import sys
import json
import time
import threading
import signal
from datetime import datetime
from typing import Dict, Any, Optional, List
from decimal import Decimal

# Import our bot
from bot import BasicBot, setup_logger, RICH_AVAILABLE, _RICH_CONSOLE

# Rich imports for enhanced UI
if RICH_AVAILABLE:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.layout import Layout
    from rich.live import Live
    from rich.text import Text
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.prompt import Prompt, Confirm
    from rich import box
    from rich.align import Align
    from rich.columns import Columns
    from rich.status import Status
else:
    Console = None
    Table = None
    Panel = None
    Layout = None
    Live = None
    Text = None
    Progress = None
    SpinnerColumn = None
    TextColumn = None
    Prompt = None
    Confirm = None
    box = None
    Align = None
    Columns = None
    Status = None

class EnhancedCLI:
    """Enhanced CLI interface with real-time updates and better UX."""
    
    def __init__(self):
        self.logger = setup_logger()
        self.console = Console() if RICH_AVAILABLE else None
        self.bot: Optional[BasicBot] = None
        self.running = False
        self.refresh_interval = 5  # seconds
        self.current_prices: Dict[str, float] = {}
        
    def initialize_bot(self) -> bool:
        """Initialize bot with credentials."""
        try:
            # Get credentials
            api_key = os.getenv("BINANCE_API_KEY")
            api_secret = os.getenv("BINANCE_API_SECRET")
            
            if not api_key or not api_secret:
                if self.console:
                    self.console.print("[red]API credentials not found in environment variables.[/red]")
                    api_key = Prompt.ask("Enter API Key")
                    api_secret = Prompt.ask("Enter API Secret", password=True)
                else:
                    api_key = input("Enter API Key: ")
                    api_secret = input("Enter API Secret: ")
            
            # Initialize bot
            self.bot = BasicBot(
                api_key=api_key,
                api_secret=api_secret,
                testnet=True,
                log_level=self.logger.level
            )
            
            # Health check
            with self._show_status("Performing health check..."):
                self.bot.health_check()
            
            return True
            
        except Exception as e:
            if self.console:
                self.console.print(f"[red]Failed to initialize bot: {e}[/red]")
            else:
                print(f"Failed to initialize bot: {e}")
            return False
    
    def _show_status(self, message: str):
        """Context manager for showing status."""
        if self.console:
            return Status(message, console=self.console)
        else:
            print(message, end="", flush=True)
            return self._dummy_context()
    
    def _dummy_context(self):
        """Dummy context manager for non-rich mode."""
        class DummyContext:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                print(" ✓")
        return DummyContext()
    
    def show_welcome(self):
        """Show welcome screen."""
        if self.console:
            welcome_text = """
[bold blue]Binance Futures Trading Bot - Enhanced CLI[/bold blue]

[green]✓[/green] Connected to Binance Futures Testnet
[green]✓[/green] Real-time account monitoring
[green]✓[/green] Interactive order placement
[green]✓[/green] Live price updates

[yellow]Press Ctrl+C to exit[/yellow]
            """
            self.console.print(Panel(welcome_text.strip(), border_style="blue"))
        else:
            print("\n" + "="*50)
            print("Binance Futures Trading Bot - Enhanced CLI")
            print("="*50)
            print("✓ Connected to Binance Futures Testnet")
            print("✓ Real-time account monitoring")
            print("✓ Interactive order placement")
            print("✓ Live price updates")
            print("\nPress Ctrl+C to exit")
            print("="*50)
    
    def get_account_summary(self) -> Dict[str, Any]:
        """Get account summary."""
        if not self.bot:
            return {}
        return self.bot.get_account_summary()
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for symbol."""
        try:
            if not self.bot:
                return None
            ticker = self.bot.client.futures_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except Exception:
            return None
    
    def create_dashboard_layout(self) -> Layout:
        """Create the main dashboard layout."""
        if not self.console:
            return None
            
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=3)
        )
        
        layout["main"].split_row(
            Layout(name="left", ratio=1),
            Layout(name="right", ratio=1)
        )
        
        return layout
    
    def update_dashboard(self, layout: Layout):
        """Update dashboard with current data."""
        if not self.console or not layout:
            return
            
        # Header
        header_text = Text("Binance Futures Trading Bot - Live Dashboard", style="bold blue")
        header_text.append(f" | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", style="dim")
        layout["header"].update(Align.center(header_text))
        
        # Account summary
        account = self.get_account_summary()
        
        # Left panel - Balances
        balance_table = Table(title="Account Balance", box=box.SIMPLE_HEAVY)
        balance_table.add_column("Asset", style="cyan")
        balance_table.add_column("Total", style="white")
        balance_table.add_column("Available", style="white")
        
        if account.get("balances"):
            for balance in account["balances"]:
                balance_table.add_row(
                    balance.get("asset", "-"),
                    balance.get("balance", "-"),
                    balance.get("availableBalance", "-")
                )
        else:
            balance_table.add_row("-", "-", "-")
        
        layout["left"].update(balance_table)
        
        # Right panel - Positions
        position_table = Table(title="Open Positions", box=box.SIMPLE_HEAVY)
        position_table.add_column("Symbol", style="cyan")
        position_table.add_column("Amount", style="white")
        position_table.add_column("Entry", style="white")
        position_table.add_column("PnL", style="white")
        position_table.add_column("Leverage", style="white")
        
        if account.get("positions"):
            for position in account["positions"]:
                pnl = float(position.get("unRealizedProfit", 0))
                pnl_style = "green" if pnl >= 0 else "red"
                position_table.add_row(
                    position.get("symbol", "-"),
                    position.get("positionAmt", "-"),
                    position.get("entryPrice", "-"),
                    Text(str(pnl), style=pnl_style),
                    position.get("leverage", "-")
                )
        else:
            position_table.add_row("-", "-", "-", "-", "-")
        
        layout["right"].update(position_table)
        
        # Footer - Quick actions
        footer_text = Text("Quick Actions: ", style="bold")
        footer_text.append("1) Place Order  ", style="cyan")
        footer_text.append("2) View Prices  ", style="cyan")
        footer_text.append("3) Account Details  ", style="cyan")
        footer_text.append("4) Exit", style="red")
        layout["footer"].update(Align.center(footer_text))
    
    def show_price_monitor(self, symbols: List[str]):
        """Show live price monitor."""
        if not self.console:
            print("\nPrice Monitor (Press Ctrl+C to return)")
            print("-" * 40)
            while True:
                try:
                    for symbol in symbols:
                        price = self.get_current_price(symbol)
                        if price:
                            print(f"{symbol}: ${price:,.2f}")
                    print("-" * 40)
                    time.sleep(2)
                except KeyboardInterrupt:
                    break
            return
        
        def update_prices():
            table = Table(title="Live Price Monitor", box=box.SIMPLE_HEAVY)
            table.add_column("Symbol", style="cyan")
            table.add_column("Price", style="white")
            table.add_column("Time", style="dim")
            
            for symbol in symbols:
                price = self.get_current_price(symbol)
                if price:
                    table.add_row(
                        symbol,
                        f"${price:,.2f}",
                        datetime.now().strftime("%H:%M:%S")
                    )
                else:
                    table.add_row(symbol, "N/A", "-")
            
            return table
        
        try:
            with Live(update_prices(), refresh_per_second=2, console=self.console) as live:
                while True:
                    live.update(update_prices())
                    time.sleep(0.5)
        except KeyboardInterrupt:
            pass
    
    def interactive_order_placement(self):
        """Interactive order placement."""
        if self.console:
            self.console.print("\n[bold]Interactive Order Placement[/bold]")
        else:
            print("\nInteractive Order Placement")
            print("-" * 30)
        
        # Get order details
        symbol = self._prompt_input("Symbol (e.g., BTCUSDT): ").upper()
        if not symbol.endswith("USDT"):
            if self.console:
                self.console.print("[red]Only USDT-M Futures symbols are supported[/red]")
            else:
                print("Only USDT-M Futures symbols are supported")
            return
        
        # Show current price
        current_price = self.get_current_price(symbol)
        if current_price:
            if self.console:
                self.console.print(f"[green]Current {symbol} price: ${current_price:,.2f}[/green]")
            else:
                print(f"Current {symbol} price: ${current_price:,.2f}")
        
        side = self._prompt_choice("Side", ["BUY", "SELL"])
        
        order_types = ["MARKET", "LIMIT", "STOP_LIMIT", "TAKE_PROFIT_LIMIT"]
        order_type = self._prompt_choice("Order Type", order_types)
        
        quantity = self._prompt_decimal("Quantity: ")
        
        # Get additional parameters based on order type
        if order_type == "LIMIT":
            price = self._prompt_decimal("Limit Price: ")
            result = self.bot.place_limit_order(symbol, side, quantity, price)
        elif order_type == "STOP_LIMIT":
            stop_price = self._prompt_decimal("Stop Price: ")
            limit_price = self._prompt_decimal("Limit Price: ")
            result = self.bot.place_stop_limit_order(symbol, side, quantity, stop_price, limit_price)
        elif order_type == "TAKE_PROFIT_LIMIT":
            stop_price = self._prompt_decimal("Stop Price: ")
            limit_price = self._prompt_decimal("Limit Price: ")
            result = self.bot.place_take_profit_limit_order(symbol, side, quantity, stop_price, limit_price)
        else:  # MARKET
            result = self.bot.place_market_order(symbol, side, quantity)
        
        # Show result
        self._show_order_result(result)
    
    def _prompt_input(self, prompt: str) -> str:
        """Get input from user."""
        if self.console:
            return Prompt.ask(prompt)
        else:
            return input(prompt).strip()
    
    def _prompt_choice(self, prompt: str, choices: List[str]) -> str:
        """Get choice from user."""
        if self.console:
            return Prompt.ask(prompt, choices=choices, default=choices[0])
        else:
            while True:
                print(f"\n{prompt}:")
                for i, choice in enumerate(choices, 1):
                    print(f"  {i}) {choice}")
                try:
                    idx = int(input("Choice: ")) - 1
                    if 0 <= idx < len(choices):
                        return choices[idx]
                except ValueError:
                    pass
                print("Invalid choice. Please try again.")
    
    def _prompt_decimal(self, prompt: str) -> Decimal:
        """Get decimal input from user."""
        while True:
            try:
                value = Decimal(self._prompt_input(prompt))
                if value <= 0:
                    raise ValueError
                return value
            except (ValueError, TypeError):
                if self.console:
                    self.console.print("[red]Please enter a positive number[/red]")
                else:
                    print("Please enter a positive number")
    
    def _show_order_result(self, result: Dict[str, Any]):
        """Show order result."""
        if self.console:
            table = Table(title="Order Result", box=box.SIMPLE_HEAVY)
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="white")
            
            for key, value in result.items():
                if value is not None:
                    table.add_row(str(key), str(value))
            
            self.console.print(table)
        else:
            print("\nOrder Result:")
            print("-" * 20)
            for key, value in result.items():
                if value is not None:
                    print(f"{key}: {value}")
            print()
    
    def show_account_details(self):
        """Show detailed account information."""
        account = self.get_account_summary()
        
        if self.console:
            # Create detailed tables
            balance_table = Table(title="Account Balances", box=box.SIMPLE_HEAVY)
            balance_table.add_column("Asset", style="cyan")
            balance_table.add_column("Total Balance", style="white")
            balance_table.add_column("Available Balance", style="white")
            
            if account.get("balances"):
                for balance in account["balances"]:
                    balance_table.add_row(
                        balance.get("asset", "-"),
                        balance.get("balance", "-"),
                        balance.get("availableBalance", "-")
                    )
            
            position_table = Table(title="Open Positions", box=box.SIMPLE_HEAVY)
            position_table.add_column("Symbol", style="cyan")
            position_table.add_column("Position Amount", style="white")
            position_table.add_column("Entry Price", style="white")
            position_table.add_column("Unrealized PnL", style="white")
            position_table.add_column("Leverage", style="white")
            position_table.add_column("Margin Type", style="white")
            
            if account.get("positions"):
                for position in account["positions"]:
                    pnl = float(position.get("unRealizedProfit", 0))
                    pnl_style = "green" if pnl >= 0 else "red"
                    position_table.add_row(
                        position.get("symbol", "-"),
                        position.get("positionAmt", "-"),
                        position.get("entryPrice", "-"),
                        Text(str(pnl), style=pnl_style),
                        position.get("leverage", "-"),
                        position.get("marginType", "-")
                    )
            
            self.console.print(Columns([balance_table, position_table]))
        else:
            print("\nAccount Details:")
            print("=" * 50)
            
            if account.get("balances"):
                print("\nBalances:")
                for balance in account["balances"]:
                    print(f"  {balance.get('asset')}: {balance.get('balance')} (Available: {balance.get('availableBalance')})")
            
            if account.get("positions"):
                print("\nOpen Positions:")
                for position in account["positions"]:
                    print(f"  {position.get('symbol')}: {position.get('positionAmt')} @ {position.get('entryPrice')}")
                    print(f"    PnL: {position.get('unRealizedProfit')}, Leverage: {position.get('leverage')}x")
            else:
                print("\nNo open positions")
    
    def run_interactive_mode(self):
        """Run interactive mode."""
        self.running = True
        
        # Setup signal handler
        def signal_handler(signum, frame):
            self.running = False
            if self.console:
                self.console.print("\n[yellow]Shutting down...[/yellow]")
            else:
                print("\nShutting down...")
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        
        # Show welcome
        self.show_welcome()
        
        # Main loop
        while self.running:
            try:
                if self.console:
                    choice = Prompt.ask(
                        "\nSelect action",
                        choices=["1", "2", "3", "4", "5", "6"],
                        default="1"
                    )
                else:
                    print("\nSelect action:")
                    print("  1) Live Dashboard")
                    print("  2) Place Order")
                    print("  3) Price Monitor")
                    print("  4) Account Details")
                    print("  5) Health Check")
                    print("  6) Exit")
                    choice = input("Choice (1-6): ").strip()
                
                if choice == "1":
                    self._run_live_dashboard()
                elif choice == "2":
                    self.interactive_order_placement()
                elif choice == "3":
                    symbols = self._prompt_input("Symbols (comma-separated, e.g., BTCUSDT,ETHUSDT): ").split(",")
                    symbols = [s.strip().upper() for s in symbols if s.strip()]
                    if symbols:
                        self.show_price_monitor(symbols)
                elif choice == "4":
                    self.show_account_details()
                elif choice == "5":
                    with self._show_status("Performing health check..."):
                        self.bot.health_check()
                    if self.console:
                        self.console.print("[green]Health check passed![/green]")
                    else:
                        print("Health check passed!")
                elif choice == "6":
                    break
                else:
                    if self.console:
                        self.console.print("[red]Invalid choice[/red]")
                    else:
                        print("Invalid choice")
                        
            except KeyboardInterrupt:
                break
            except Exception as e:
                if self.console:
                    self.console.print(f"[red]Error: {e}[/red]")
                else:
                    print(f"Error: {e}")
    
    def _run_live_dashboard(self):
        """Run live dashboard."""
        if not self.console:
            print("\nLive Dashboard (Press Ctrl+C to return)")
            print("-" * 50)
            try:
                while True:
                    account = self.get_account_summary()
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Account Summary:")
                    
                    if account.get("balances"):
                        for balance in account["balances"]:
                            print(f"  {balance.get('asset')}: {balance.get('balance')}")
                    
                    if account.get("positions"):
                        for position in account["positions"]:
                            print(f"  {position.get('symbol')}: {position.get('positionAmt')} (PnL: {position.get('unRealizedProfit')})")
                    
                    time.sleep(self.refresh_interval)
            except KeyboardInterrupt:
                pass
            return
        
        layout = self.create_dashboard_layout()
        
        try:
            with Live(layout, refresh_per_second=1, console=self.console) as live:
                while True:
                    self.update_dashboard(layout)
                    time.sleep(1)
        except KeyboardInterrupt:
            pass

def main():
    """Main entry point."""
    cli = EnhancedCLI()
    
    if not cli.initialize_bot():
        sys.exit(1)
    
    cli.run_interactive_mode()

if __name__ == "__main__":
    main()

