#!/usr/bin/env python3
"""
Trading Bot Launcher

A simple launcher that allows users to choose between different UI interfaces:
1. Original CLI
2. Enhanced CLI with live updates
3. Web UI
"""

import os
import sys
import subprocess
from typing import Optional

def check_dependencies() -> dict:
    """Check which dependencies are available."""
    deps = {
        'rich': False,
        'flask': False,
        'python-binance': False
    }
    
    try:
        import rich
        deps['rich'] = True
    except ImportError:
        pass
    
    try:
        import flask
        deps['flask'] = True
    except ImportError:
        pass
    
    try:
        import binance
        deps['python-binance'] = True
    except ImportError:
        pass
    
    return deps

def install_dependencies():
    """Install missing dependencies."""
    print("Installing missing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("Dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to install dependencies: {e}")
        return False

def show_menu():
    """Show the main menu."""
    print("\n" + "="*60)
    print("🚀 Binance Futures Trading Bot - UI Launcher")
    print("="*60)
    print()
    print("Choose your preferred interface:")
    print()
    print("  1) 📱 Web UI (Modern browser-based interface)")
    print("     • Real-time dashboard")
    print("     • Interactive order forms")
    print("     • Account monitoring")
    print("     • Configuration management")
    print()
    print("  2) 💻 Enhanced CLI (Rich terminal interface)")
    print("     • Live dashboard with real-time updates")
    print("     • Interactive order placement")
    print("     • Price monitoring")
    print("     • Colorful tables and progress bars")
    print()
    print("  3) 🔧 Original CLI (Simple text interface)")
    print("     • Basic menu-driven interface")
    print("     • Order placement")
    print("     • Account summary")
    print("     • Works without additional dependencies")
    print()
    print("  4) 📦 Install/Update Dependencies")
    print("  5) ❌ Exit")
    print()
    print("="*60)

def run_web_ui():
    """Run the web UI."""
    print("\n🌐 Starting Web UI...")
    print("The web interface will open in your browser at: http://localhost:5000")
    print("Press Ctrl+C to stop the web server")
    print()
    
    try:
        import web_ui
        # The web_ui module will handle the Flask app startup
    except ImportError as e:
        print(f"Error: Could not import web_ui module: {e}")
        print("Make sure web_ui.py is in the same directory")
        return False
    except Exception as e:
        print(f"Error starting web UI: {e}")
        return False

def run_enhanced_cli():
    """Run the enhanced CLI."""
    print("\n💻 Starting Enhanced CLI...")
    print("Press Ctrl+C to exit")
    print()
    
    try:
        import enhanced_cli
        # The enhanced_cli module will handle the CLI startup
    except ImportError as e:
        print(f"Error: Could not import enhanced_cli module: {e}")
        print("Make sure enhanced_cli.py is in the same directory")
        return False
    except Exception as e:
        print(f"Error starting enhanced CLI: {e}")
        return False

def run_original_cli():
    """Run the original CLI."""
    print("\n🔧 Starting Original CLI...")
    print("Press Ctrl+C to exit")
    print()
    
    try:
        import bot
        # The bot module will handle the CLI startup
    except ImportError as e:
        print(f"Error: Could not import bot module: {e}")
        print("Make sure bot.py is in the same directory")
        return False
    except Exception as e:
        print(f"Error starting original CLI: {e}")
        return False

def check_credentials():
    """Check if API credentials are set."""
    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")
    
    if not api_key or not api_secret:
        print("\n⚠️  API Credentials Not Found")
        print("="*40)
        print("You need to set your Binance Futures Testnet API credentials.")
        print()
        print("Option 1: Set environment variables (recommended):")
        print("  export BINANCE_API_KEY=your_testnet_key")
        print("  export BINANCE_API_SECRET=your_testnet_secret")
        print()
        print("Option 2: You'll be prompted to enter them when starting the bot")
        print()
        print("Get your testnet API keys from: https://testnet.binancefuture.com")
        print()
        
        response = input("Continue anyway? (y/N): ").strip().lower()
        if response != 'y':
            return False
    
    return True

def main():
    """Main launcher function."""
    # Check credentials first
    if not check_credentials():
        print("Exiting...")
        return
    
    while True:
        show_menu()
        
        try:
            choice = input("Enter your choice (1-5): ").strip()
        except KeyboardInterrupt:
            print("\n\nGoodbye! 👋")
            break
        
        if choice == "1":
            deps = check_dependencies()
            if not deps['flask']:
                print("\n❌ Flask is required for the Web UI")
                print("Installing dependencies...")
                if not install_dependencies():
                    continue
            
            if run_web_ui():
                break
            else:
                input("\nPress Enter to continue...")
        
        elif choice == "2":
            deps = check_dependencies()
            if not deps['rich']:
                print("\n❌ Rich is required for the Enhanced CLI")
                print("Installing dependencies...")
                if not install_dependencies():
                    continue
            
            if run_enhanced_cli():
                break
            else:
                input("\nPress Enter to continue...")
        
        elif choice == "3":
            deps = check_dependencies()
            if not deps['python-binance']:
                print("\n❌ python-binance is required")
                print("Installing dependencies...")
                if not install_dependencies():
                    continue
            
            if run_original_cli():
                break
            else:
                input("\nPress Enter to continue...")
        
        elif choice == "4":
            if install_dependencies():
                input("\nPress Enter to continue...")
        
        elif choice == "5":
            print("\nGoodbye! 👋")
            break
        
        else:
            print("\n❌ Invalid choice. Please enter 1-5.")
            input("Press Enter to continue...")

if __name__ == "__main__":
    main()

