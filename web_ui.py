#!/usr/bin/env python3
"""
Lightweight Web UI for Binance Futures Trading Bot

A simple Flask-based web interface that provides a modern UI for the trading bot.
Features:
- Real-time account dashboard
- Order placement forms
- Order history
- Configuration management
- Responsive design
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from werkzeug.exceptions import BadRequest

# Import our bot
from bot import BasicBot, setup_logger

# Setup logging
logger = setup_logger()

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')

# Global bot instance
bot_instance: Optional[BasicBot] = None

def get_bot() -> BasicBot:
    """Get or create bot instance with credentials from environment or config."""
    global bot_instance
    
    if bot_instance is None:
        api_key = os.getenv("BINANCE_API_KEY")
        api_secret = os.getenv("BINANCE_API_SECRET")
        
        if not api_key or not api_secret:
            raise ValueError("API credentials not found. Set BINANCE_API_KEY and BINANCE_API_SECRET environment variables.")
        
        bot_instance = BasicBot(
            api_key=api_key,
            api_secret=api_secret,
            testnet=True,
            log_level=logging.INFO
        )
        
        # Perform health check
        try:
            bot_instance.health_check()
            logger.info("Bot initialized successfully")
        except Exception as e:
            logger.error(f"Bot health check failed: {e}")
            raise
    
    return bot_instance

@app.route('/')
def dashboard():
    """Main dashboard showing account summary and recent activity."""
    try:
        bot = get_bot()
        account_summary = bot.get_account_summary()
        
        # Get recent orders (simplified - in production you'd want to store this)
        recent_orders = get_recent_orders()
        
        return render_template('dashboard.html', 
                             account=account_summary,
                             recent_orders=recent_orders)
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        flash(f"Error loading dashboard: {str(e)}", 'error')
        return render_template('error.html', error=str(e))

@app.route('/orders')
def orders():
    """Order management page."""
    return render_template('orders.html')

@app.route('/api/account')
def api_account():
    """API endpoint for account summary."""
    try:
        bot = get_bot()
        summary = bot.get_account_summary()
        return jsonify(summary)
    except Exception as e:
        logger.error(f"API account error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/place_order', methods=['POST'])
def api_place_order():
    """API endpoint for placing orders."""
    try:
        bot = get_bot()
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        order_type = data.get('type')
        symbol = data.get('symbol', '').upper()
        side = data.get('side', '').upper()
        quantity = data.get('quantity')
        
        if not all([order_type, symbol, side, quantity]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Validate symbol
        if not symbol.endswith('USDT'):
            return jsonify({'error': 'Only USDT-M Futures symbols are supported'}), 400
        
        result = None
        
        if order_type == 'MARKET':
            result = bot.place_market_order(symbol=symbol, side=side, quantity=quantity)
        elif order_type == 'LIMIT':
            price = data.get('price')
            if not price:
                return jsonify({'error': 'Price required for limit orders'}), 400
            result = bot.place_limit_order(symbol=symbol, side=side, quantity=quantity, price=price)
        elif order_type == 'STOP_LIMIT':
            stop_price = data.get('stop_price')
            limit_price = data.get('limit_price')
            if not all([stop_price, limit_price]):
                return jsonify({'error': 'Stop price and limit price required for stop-limit orders'}), 400
            result = bot.place_stop_limit_order(
                symbol=symbol, side=side, quantity=quantity,
                stop_price=stop_price, limit_price=limit_price
            )
        elif order_type == 'TAKE_PROFIT_LIMIT':
            stop_price = data.get('stop_price')
            limit_price = data.get('limit_price')
            if not all([stop_price, limit_price]):
                return jsonify({'error': 'Stop price and limit price required for take-profit limit orders'}), 400
            result = bot.place_take_profit_limit_order(
                symbol=symbol, side=side, quantity=quantity,
                stop_price=stop_price, limit_price=limit_price
            )
        else:
            return jsonify({'error': f'Unsupported order type: {order_type}'}), 400
        
        # Store order for history (simplified)
        store_order(result)
        
        return jsonify({
            'success': True,
            'order': result,
            'message': f'{order_type} order placed successfully'
        })
        
    except Exception as e:
        logger.error(f"Order placement error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health')
def api_health():
    """API endpoint for health check."""
    try:
        bot = get_bot()
        bot.health_check()
        return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

# Simple in-memory storage for demo (use database in production)
_orders_history: List[Dict[str, Any]] = []

def store_order(order_data: Dict[str, Any]) -> None:
    """Store order in history."""
    order_data['timestamp'] = datetime.now().isoformat()
    _orders_history.insert(0, order_data)  # Add to beginning
    # Keep only last 50 orders
    if len(_orders_history) > 50:
        _orders_history.pop()

def get_recent_orders() -> List[Dict[str, Any]]:
    """Get recent orders."""
    return _orders_history[:10]  # Return last 10 orders

@app.route('/api/orders')
def api_orders():
    """API endpoint for order history."""
    return jsonify(get_recent_orders())

@app.route('/config')
def config():
    """Configuration page."""
    return render_template('config.html')

@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    """API endpoint for configuration management."""
    if request.method == 'GET':
        return jsonify({
            'api_key_set': bool(os.getenv('BINANCE_API_KEY')),
            'api_secret_set': bool(os.getenv('BINANCE_API_SECRET')),
            'testnet': True  # Always testnet for safety
        })
    
    elif request.method == 'POST':
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # In production, you'd want to store these securely
        # For demo purposes, we'll just validate them
        api_key = data.get('api_key', '').strip()
        api_secret = data.get('api_secret', '').strip()
        
        if not api_key or not api_secret:
            return jsonify({'error': 'API key and secret are required'}), 400
        
        # Test the credentials
        try:
            test_bot = BasicBot(api_key=api_key, api_secret=api_secret, testnet=True)
            test_bot.health_check()
            
            # If successful, update environment (for this session only)
            os.environ['BINANCE_API_KEY'] = api_key
            os.environ['BINANCE_API_SECRET'] = api_secret
            
            # Reset global bot instance to use new credentials
            global bot_instance
            bot_instance = None
            
            return jsonify({'success': True, 'message': 'Configuration updated successfully'})
            
        except Exception as e:
            return jsonify({'error': f'Invalid credentials: {str(e)}'}), 400

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    print("Starting Binance Trading Bot Web UI...")
    print("Open your browser to: http://localhost:5000")
    print("Press Ctrl+C to stop")
    
    app.run(debug=True, host='0.0.0.0', port=5000)

