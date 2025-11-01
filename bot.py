import os
import requests
import json
import time
import re
import numpy as np
from binance.client import Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class FullyAutonomousFutureTrader:
    def __init__(self):
        # Load config from .env file
        self.binance_api_key = os.getenv('BINANCE_API_KEY')
        self.binance_secret = os.getenv('BINANCE_SECRET_KEY')
        self.deepseek_key = os.getenv('DEEPSEEK_API_KEY')
        
        # Trading parameters from .env
        self.trade_size_usd = int(os.getenv('TRADE_SIZE', 100))
        self.leverage = int(os.getenv('LEVERAGE', 3))
        self.risk_percentage = float(os.getenv('RISK_PERCENTAGE', 1.0))
        
        # Initialize Binance client
        self.binance = Client(self.binance_api_key, self.binance_secret)
        
        self.available_pairs = ["ETHUSDT", "SOLUSDT", "ADAUSDT", "XRPUSDT"]
        self.active_trade = None
        
        # Validate that all required keys are present
        self.validate_config()
        
        # Setup futures
        self.setup_futures()
    
    def validate_config(self):
        """Check if all required environment variables are set"""
        required_vars = ['BINANCE_API_KEY', 'BINANCE_SECRET_KEY', 'DEEPSEEK_API_KEY']
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            raise Exception(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        print("✅ Configuration loaded successfully!")
        print(f"   Trade Size: ${self.trade_size_usd}")
        print(f"   Leverage: {self.leverage}x")
        print(f"   Risk: {self.risk_percentage}%")
    
    def setup_futures(self):
        """Setup futures trading with leverage from .env"""
        try:
            for pair in self.available_pairs:
                # Set leverage from .env
                self.binance.futures_change_leverage(
                    symbol=pair,
                    leverage=self.leverage
                )
                print(f"🎯 {pair} leverage set to {self.leverage}x")
                
            print("✅ Futures setup completed!")
            
        except Exception as e:
            print(f"❌ Futures setup failed: {e}")
    
    def run_fully_autonomous(self):
        """Main trading loop"""
        print("🚀 FULLY AUTONOMOUS FUTURES BOT STARTED!")
        print("⚙️  Configuration: .env file")
        print(f"💵 Trade Size: ${self.trade_size_usd}")
        print(f"📈 Leverage: {self.leverage}x")
        print(f"🎯 Risk: {self.risk_percentage}%")
        
        while True:
            try:
                # 1. Get market data
                market_data = self.get_detailed_market_data()
                
                # 2. Get AI decision
                decision = self.get_deepseek_autonomous_decision(market_data)
                
                # 3. Execute trade
                if decision["action"] == "TRADE" and decision["confidence"] >= 70:
                    if not self.active_trade:
                        print(f"🎯 EXECUTING: {decision['pair']} {decision['direction']}")
                        self.execute_autonomous_trade(decision)
                    else:
                        print("⏳ Trade active, waiting...")
                else:
                    print(f"⏸️ WAITING: {decision['reason']}")
                
                # 4. Check current trade
                self.check_autonomous_exit()
                
                time.sleep(300)  # 5 minutes
                
            except Exception as e:
                print(f"❌ Error: {e}")
                time.sleep(60)
    
    def get_deepseek_autonomous_decision(self, market_data):
        """DeepSeek AI decision with dynamic trade size"""
        
        prompt = f"""
        AUTONOMOUS TRADING ANALYSIS:
        
        CONFIGURATION:
        - Trade Size: ${self.trade_size_usd}
        - Leverage: {self.leverage}x
        - Risk: {self.risk_percentage}%
        - Available Pairs: {self.available_pairs}
        
        MARKET DATA: {json.dumps(market_data, indent=2)}
        
        YOUR TASK: Analyze and make trading decisions based on the above configuration.
        
        RESPONSE (JSON):
        {{
            "action": "TRADE/SKIP",
            "pair": "SYMBOL",
            "direction": "LONG/SHORT",
            "entry_price": number,
            "stop_loss": number,
            "take_profit": number,
            "position_size_usd": {self.trade_size_usd},
            "confidence": 0-100,
            "reason": "Detailed technical analysis..."
        }}
        """
        
        headers = {
            "Authorization": f"Bearer {self.deepseek_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 1000
        }
        
        try:
            response = requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            
            print("❌ API failed, using simulation")
            return self.get_fallback_decision(market_data)
                
        except Exception as e:
            print(f"❌ API error: {e}")
            return self.get_fallback_decision(market_data)

    def get_safe_quantity(self, pair, entry_price):
        """Safe quantity calculation with precision handling"""
        try:
            # Get symbol info from exchange
            symbol_info = self.binance.futures_exchange_info()
            pair_info = next((s for s in symbol_info['symbols'] if s['symbol'] == pair), None)
            
            if pair_info:
                lot_size_filter = next((f for f in pair_info['filters'] if f['filterType'] == 'LOT_SIZE'), None)
                if lot_size_filter:
                    min_qty = float(lot_size_filter['minQty'])
                    step_size = float(lot_size_filter['stepSize'])
                    
                    # Calculate ideal quantity
                    quantity = self.trade_size_usd / entry_price
                    
                    # Ensure minimum quantity
                    quantity = max(quantity, min_qty)
                    
                    # Round to step size
                    precision = self.get_step_precision(step_size)
                    quantity = (quantity // step_size) * step_size
                    quantity = round(quantity, precision)
                    
                    print(f"🔧 Quantity Calculation:")
                    print(f"   MinQty: {min_qty}")
                    print(f"   StepSize: {step_size}") 
                    print(f"   Precision: {precision} decimals")
                    print(f"   Final Quantity: {quantity}")
                    
                    return quantity
                    
        except Exception as e:
            print(f"⚠️ Precision error, using fallback: {e}")
        
        # Fallback to manual precision
        return self.apply_pair_precision(pair, self.trade_size_usd / entry_price)

    def get_step_precision(self, step_size):
        """Calculate precision from step size"""
        step_str = str(step_size).rstrip('0')
        if '.' in step_str:
            return len(step_str.split('.')[1])
        else:
            return 0

    def apply_pair_precision(self, pair, quantity):
        """Apply pair-specific quantity precision"""
        precision_map = {
            "ETHUSDT": 3,   # 0.001 ETH
            "SOLUSDT": 1,   # 0.1 SOL
            "ADAUSDT": 0,   # 1 ADA (whole numbers only)
            "XRPUSDT": 0,   # 1 XRP (whole numbers only)
        }
        
        precision = precision_map.get(pair, 0)
        quantity = round(quantity, precision)
        
        # Ensure whole numbers for ADA and XRP
        if precision == 0:
            quantity = int(quantity)
            
        return quantity

    def execute_autonomous_trade(self, decision):
    """Execute trade with MARKET ENTRY + LIMIT TP/SL - FIXED VERSION"""
    try:
        pair = decision["pair"]
        direction = decision["direction"]
        current_price = decision["entry_price"]  # Use as reference price
        stop_loss = decision["stop_loss"]
        take_profit = decision["take_profit"]
        
        # Get current market price for accurate quantity calculation
        ticker = self.binance.futures_symbol_ticker(symbol=pair)
        current_market_price = float(ticker['price'])
        
        print(f"🔧 Initial Calculation:")
        print(f"   Trade Size: ${self.trade_size_usd}")
        print(f"   Market Price: ${current_market_price}")
        print(f"   Raw Quantity: {self.trade_size_usd / current_market_price}")
        
        # Get safe quantity with proper precision
        quantity = self.get_safe_quantity(pair, current_market_price)
        
        # Final validation - check if quantity meets minimum notional
        notional_value = current_market_price * quantity
        min_notional = 5  # Binance minimum is usually $5-$10
        
        if notional_value < min_notional:
            print(f"⚠️ Notional value too low: ${notional_value:.2f}")
            # Adjust quantity to meet minimum
            quantity = min_notional / current_market_price
            quantity = self.get_safe_quantity(pair, current_market_price)
            print(f"⚠️ Adjusted quantity: {quantity}")
        
        if quantity <= 0:
            print(f"❌ Invalid quantity: {quantity}")
            return
        
        print(f"🔧 Trade Execution Details:")
        print(f"   Pair: {pair}")
        print(f"   Direction: {direction}")
        print(f"   Current Market Price: ${current_market_price}")
        print(f"   Stop Loss: ${stop_loss}")
        print(f"   Take Profit: ${take_profit}")
        print(f"   Quantity: {quantity}")
        print(f"   Size: ${self.trade_size_usd}")
        print(f"   Notional Value: ${current_market_price * quantity:.2f}")
        print(f"   Leverage: {self.leverage}x")
        
        # 1. MARKET ENTRY - Immediate execution
        if direction == "LONG":
            entry_order = self.binance.futures_create_order(
                symbol=pair,
                side='BUY',
                type='MARKET',
                quantity=quantity
            )
            actual_entry_price = float(entry_order['avgPrice'])
            print(f"✅ MARKET BUY EXECUTED: {quantity} {pair} @ ${actual_entry_price}")
        else:  # SHORT
            entry_order = self.binance.futures_create_order(
                symbol=pair,
                side='SELL',
                type='MARKET',
                quantity=quantity
            )
            actual_entry_price = float(entry_order['avgPrice'])
            print(f"✅ MARKET SELL EXECUTED: {quantity} {pair} @ ${actual_entry_price}")
        
        # Wait a moment for position to open
        time.sleep(2)
        
        # 2. STOP LOSS with MARKET order (more reliable)
        if direction == "LONG":
            sl_order = self.binance.futures_create_order(
                symbol=pair,
                side='SELL',
                type='STOP_MARKET',  # Use MARKET for reliability
                quantity=quantity,
                stopPrice=str(stop_loss),
                timeInForce='GTC',
                reduceOnly=True
            )
            print(f"🛡️ STOP LOSS SET: SELL @ ${stop_loss}")
        else:  # SHORT
            sl_order = self.binance.futures_create_order(
                symbol=pair,
                side='BUY',
                type='STOP_MARKET',  # Use MARKET for reliability
                quantity=quantity,
                stopPrice=str(stop_loss),
                timeInForce='GTC',
                reduceOnly=True
            )
            print(f"🛡️ STOP LOSS SET: BUY @ ${stop_loss}")
        
        # 3. TAKE PROFIT with LIMIT order
        if direction == "LONG":
            tp_order = self.binance.futures_create_order(
                symbol=pair,
                side='SELL',
                type='LIMIT',
                quantity=quantity,
                price=str(take_profit),
                timeInForce='GTC',
                reduceOnly=True
            )
            print(f"🎯 TAKE PROFIT SET: SELL @ ${take_profit}")
        else:  # SHORT
            tp_order = self.binance.futures_create_order(
                symbol=pair,
                side='BUY',
                type='LIMIT',
                quantity=quantity,
                price=str(take_profit),
                timeInForce='GTC',
                reduceOnly=True
            )
            print(f"🎯 TAKE PROFIT SET: BUY @ ${take_profit}")
        
        # Save trade info
        self.active_trade = {
            "pair": pair,
            "direction": direction,
            "entry_price": actual_entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "quantity": quantity,
            "sl_order_id": sl_order['orderId'],
            "tp_order_id": tp_order['orderId'],
            "entry_time": time.time(),
            "size_usd": self.trade_size_usd,
            "leverage": self.leverage,
            "status": "ACTIVE"
        }
        
        print(f"✅ ALL ORDERS EXECUTED SUCCESSFULLY!")
        print(f"   Position is now ACTIVE")
        print(f"   Actual Entry: ${actual_entry_price}")
        
    except Exception as e:
        print(f"❌ Trade execution failed: {e}")
        # Debug information
        print(f"   Debug - Pair: {pair}")
        print(f"   Debug - Quantity: {quantity}")
        print(f"   Debug - Market Price: {current_market_price}")
            # If any order fails, close position
            try:
                self.emergency_close_position(pair, direction, quantity)
            except:
                pass

    def emergency_close_position(self, pair, direction, quantity):
        """Emergency close position if something goes wrong"""
        try:
            if direction == "LONG":
                close_side = 'SELL'
            else:
                close_side = 'BUY'
            
            self.binance.futures_create_order(
                symbol=pair,
                side=close_side,
                type='MARKET',
                quantity=quantity
            )
            print(f"🚨 EMERGENCY POSITION CLOSED: {quantity} {pair}")
        except Exception as e:
            print(f"❌ Emergency close failed: {e}")

    def check_autonomous_exit(self):
        """Check if orders are filled or need management"""
        if not self.active_trade:
            return
            
        try:
            pair = self.active_trade["pair"]
            
            # Check if we still have an active position
            positions = self.binance.futures_position_information(symbol=pair)
            position = next((p for p in positions if float(p['positionAmt']) != 0), None)
            
            if not position:
                print("💰 POSITION CLOSED! All orders completed.")
                self.active_trade = None
                return
            
            # Check TP/SL orders status
            try:
                tp_order = self.binance.futures_get_order(
                    symbol=pair,
                    orderId=self.active_trade["tp_order_id"]
                )
                sl_order = self.binance.futures_get_order(
                    symbol=pair,
                    orderId=self.active_trade["sl_order_id"]
                )
                
                if tp_order['status'] == 'FILLED':
                    print("🎯 TAKE PROFIT HIT! Trade completed successfully.")
                    self.active_trade = None
                elif sl_order['status'] == 'FILLED':
                    print("🛡️ STOP LOSS HIT! Trade closed.")
                    self.active_trade = None
                    
            except Exception as e:
                # Orders might be cancelled or modified, just continue monitoring
                pass
                
        except Exception as e:
            print(f"❌ Order check error: {e}")

    def cancel_all_orders(self, pair):
        """Cancel all orders for a pair"""
        try:
            # Cancel all open orders for this pair
            self.binance.futures_cancel_all_open_orders(symbol=pair)
            print(f"🗑️ Cancelled all orders for {pair}")
        except Exception as e:
            print(f"❌ Cancel error: {e}")

    def close_autonomous_trade(self, reason):
        """Close trade manually with market order"""
        try:
            pair = self.active_trade["pair"]
            direction = self.active_trade["direction"]
            quantity = self.active_trade["quantity"]
            
            # 1. Cancel all open orders first
            self.cancel_all_orders(pair)
            
            # 2. Close position with market order
            if direction == "LONG":
                close_side = 'SELL'
            else:
                close_side = 'BUY'
            
            order = self.binance.futures_create_order(
                symbol=pair,
                side=close_side,
                type='MARKET',
                quantity=quantity
            )
            
            exit_price = float(order['avgPrice'])
            entry_price = self.active_trade["entry_price"]
            
            if direction == "LONG":
                pnl = (exit_price - entry_price) * quantity
            else:
                pnl = (entry_price - exit_price) * quantity
            
            pnl_percent = (pnl / self.trade_size_usd) * 100
            
            print(f"🔚 MANUAL TRADE CLOSE: {reason}")
            print(f"   Exit Price: ${exit_price}")
            print(f"   P&L: ${pnl:+.2f} ({pnl_percent:+.2f}%)")
            
            self.active_trade = None
            
        except Exception as e:
            print(f"❌ Manual close error: {e}")

    def get_detailed_market_data(self):
        """Get comprehensive market data"""
        market_data = {}
        
        for pair in self.available_pairs:
            try:
                # Current price
                ticker = self.binance.futures_symbol_ticker(symbol=pair)
                price = float(ticker['price'])
                
                # Historical data
                klines = self.binance.futures_klines(
                    symbol=pair,
                    interval=Client.KLINE_INTERVAL_15MINUTE,
                    limit=20
                )
                
                closes = [float(k[4]) for k in klines]
                highs = [float(k[2]) for k in klines]
                lows = [float(k[3]) for k in klines]
                volumes = [float(k[5]) for k in klines]
                
                # Basic indicators
                current_volume = volumes[-1] if volumes else 0
                avg_volume = np.mean(volumes[-10:]) if len(volumes) >= 10 else current_volume
                
                market_data[pair] = {
                    'price': price,
                    'high_24h': max(highs) if highs else price,
                    'low_24h': min(lows) if lows else price,
                    'volume': current_volume,
                    'volume_ratio': current_volume / avg_volume if avg_volume > 0 else 1,
                    'change_24h': ((closes[-1] - closes[0]) / closes[0]) * 100 if closes else 0
                }
                
            except Exception as e:
                print(f"❌ Market data error for {pair}: {e}")
                continue
                
        return market_data
    
    def get_fallback_decision(self, market_data):
        """Fallback decision when API fails"""
        for pair, data in market_data.items():
            price = data['price']
            change = data.get('change_24h', 0)
            volume_ratio = data.get('volume_ratio', 1)
            
            # Simple trading logic
            if change < -2 and volume_ratio > 1.2:
                return {
                    "action": "TRADE",
                    "pair": pair,
                    "direction": "LONG",
                    "entry_price": price,  # Current price for market entry
                    "stop_loss": round(price * 0.98, 4),
                    "take_profit": round(price * 1.02, 4),
                    "position_size_usd": self.trade_size_usd,
                    "confidence": 70,
                    "reason": f"Fallback: {pair} oversold with high volume, potential bounce"
                }
            elif change > 2 and volume_ratio > 1.2:
                return {
                    "action": "TRADE",
                    "pair": pair,
                    "direction": "SHORT",
                    "entry_price": price,  # Current price for market entry
                    "stop_loss": round(price * 1.02, 4),
                    "take_profit": round(price * 0.98, 4),
                    "position_size_usd": self.trade_size_usd,
                    "confidence": 70,
                    "reason": f"Fallback: {pair} overbought with high volume, potential pullback"
                }
        
        return {
            "action": "SKIP",
            "confidence": 50,
            "reason": "Fallback: No clear trading signals"
        }

# 🚀 START BOT
if __name__ == "__main__":
    try:
        bot = FullyAutonomousFutureTrader()
        bot.run_fully_autonomous()
    except Exception as e:
        print(f"❌ Failed to start bot: {e}")
        print("💡 Check your .env file configuration")
