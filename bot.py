import os
import requests
import json
import time
import re
import numpy as np  # ✅ ADD THIS LINE
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
    
    def execute_autonomous_trade(self, decision):
    """Fixed version with proper precision handling"""
    try:
        pair = decision["pair"]
        direction = decision["direction"]
        entry_price = decision["entry_price"]
        
        # Get safe quantity with proper precision
        quantity = self.get_safe_quantity(pair, entry_price)
        
        # Final validation
        if quantity <= 0:
            print(f"❌ Invalid quantity: {quantity}")
            return
        
        print(f"🔧 Trade Execution Details:")
        print(f"   Pair: {pair}")
        print(f"   Direction: {direction}")
        print(f"   Entry: ${entry_price}")
        print(f"   Quantity: {quantity}")
        print(f"   Size: ${self.trade_size_usd}")
        print(f"   Leverage: {self.leverage}x")
        print(f"   Effective: ${self.trade_size_usd * self.leverage}")
        print(f"   Notional: ${entry_price * quantity:.2f}")
        
        if direction == "LONG":
            order = self.binance.futures_create_order(
                symbol=pair,
                side='BUY',
                type='LIMIT',
                quantity=quantity,
                price=str(entry_price),
                timeInForce='GTC'
            )
        else:  # SHORT
            order = self.binance.futures_create_order(
                symbol=pair,
                side='SELL',
                type='LIMIT',
                quantity=quantity,
                price=str(entry_price),
                timeInForce='GTC'
            )
        
        # Save trade info
        self.active_trade = {
            "pair": pair,
            "direction": direction,
            "entry_price": entry_price,
            "stop_loss": decision["stop_loss"],
            "take_profit": decision["take_profit"],
            "quantity": quantity,
            "order_id": order['orderId'],
            "entry_time": time.time(),
            "size_usd": self.trade_size_usd,
            "leverage": self.leverage
        }
        
        print(f"✅ TRADE EXECUTED: {direction} {pair}")
        print(f"   SL: ${decision['stop_loss']}, TP: ${decision['take_profit']}")
        print(f"   Reason: {decision['reason']}")
        
    except Exception as e:
        print(f"❌ Trade failed: {e}")
        # Debug info
        print(f"   Debug - Pair: {pair}, Price: {entry_price}")
        print(f"   Debug - Calculated Quantity: {self.trade_size_usd / entry_price}")
    
    def check_autonomous_exit(self):
        """Check and manage current trade"""
        if not self.active_trade:
            return
            
        try:
            pair = self.active_trade["pair"]
            
            # Get current price
            ticker = self.binance.futures_symbol_ticker(symbol=pair)
            current_price = float(ticker['price'])
            
            sl = self.active_trade["stop_loss"]
            tp = self.active_trade["take_profit"]
            
            # Check exit conditions
            exit_reason = None
            
            if self.active_trade["direction"] == "LONG":
                if current_price <= sl:
                    exit_reason = "STOP LOSS"
                elif current_price >= tp:
                    exit_reason = "TAKE PROFIT"
            else:  # SHORT
                if current_price >= sl:
                    exit_reason = "STOP LOSS"
                elif current_price <= tp:
                    exit_reason = "TAKE PROFIT"
            
            if exit_reason:
                self.close_autonomous_trade(exit_reason, current_price)
                
        except Exception as e:
            print(f"❌ Exit check error: {e}")
    
    def close_autonomous_trade(self, reason, exit_price):
        """Close trade and report results"""
        try:
            pair = self.active_trade["pair"]
            direction = self.active_trade["direction"]
            
            # Close position
            if direction == "LONG":
                close_side = 'SELL'
            else:
                close_side = 'BUY'
            
            order = self.binance.futures_create_order(
                symbol=pair,
                side=close_side,
                type='MARKET',
                quantity=self.active_trade["quantity"]
            )
            
            # Calculate P&L
            entry_price = self.active_trade["entry_price"]
            quantity = self.active_trade["quantity"]
            
            if direction == "LONG":
                pnl = (exit_price - entry_price) * quantity
            else:
                pnl = (entry_price - exit_price) * quantity
            
            pnl_percent = (pnl / self.trade_size_usd) * 100
            
            print(f"🔚 TRADE CLOSED: {reason}")
            print(f"   Exit Price: ${exit_price}")
            print(f"   P&L: ${pnl:+.2f} ({pnl_percent:+.2f}%)")
            print(f"   Leverage: {self.active_trade['leverage']}x")
            
            # Duration
            duration = time.time() - self.active_trade["entry_time"]
            print(f"   Duration: {duration/60:.1f} minutes")
            
            self.active_trade = None
            
        except Exception as e:
            print(f"❌ Close error: {e}")
    
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
                    "entry_price": round(price * 0.998, 4),
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
                    "entry_price": round(price * 1.002, 4),
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
