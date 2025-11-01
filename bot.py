import requests
import json
import time
import re
from binance.client import Client

class SimpleFutureTrader:
    def __init__(self, binance_api_key, binance_secret, deepseek_api_key):
        self.binance = Client(binance_api_key, binance_secret)
        self.deepseek_key = deepseek_api_key
        
        # Fixed parameters - YOU set leverage in Binance app
        self.trade_size_usd = 100  # Fixed $100 position size
        self.available_pairs = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "XRPUSDT"]
        self.active_trade = None
    
    def run_simple_future(self):
        """Simple futures trading - $100 fixed, leverage set in Binance app"""
        print("🚀 SIMPLE FUTURES BOT STARTED!")
        print("💵 Fixed trade size: $100")
        print("⚡ Leverage: YOU set in Binance app")
        print("🤖 DeepSeek decides entries/exits only")
        
        while True:
            try:
                # 1. Get market data
                market_data = self.get_futures_market_data()
                
                # 2. Get AI decision
                decision = self.get_deepseek_decision(market_data)
                
                # 3. Execute if signal good
                if decision["action"] == "TRADE" and decision["confidence"] >= 70:
                    if not self.active_trade:
                        print(f"🎯 EXECUTING: {decision['pair']} {decision['direction']}")
                        self.execute_simple_trade(decision)
                    else:
                        print("⏳ Trade active, waiting...")
                else:
                    print(f"⏸️ WAITING: {decision['reason']}")
                
                # 4. Check current trade
                self.check_current_trade()
                
                time.sleep(300)  # 5 minutes
                
            except Exception as e:
                print(f"❌ Error: {e}")
                time.sleep(60)
    
    def get_deepseek_decision(self, market_data):
        """DeepSeek က entry/exit points ပဲဆုံးဖြတ်ခိုင်းမယ်"""
        
        prompt = f"""
        SIMPLE FUTURES TRADING DECISION:
        
        FIXED TRADE SIZE: $100
        AVAILABLE PAIRS: {self.available_pairs}
        LEVERAGE: SET IN BINANCE APP (you don't control this)
        CURRENT MARKET: {json.dumps(market_data, indent=2)}
        
        YOUR TASK: Only decide entry/exit points
        - Analyze which pair to trade
        - Set entry price, stop loss, take profit
        - $100 position size is FIXED
        - Leverage already set in Binance app
        
        RESPONSE (JSON):
        {{
            "action": "TRADE/SKIP",
            "pair": "BTCUSDT", 
            "direction": "LONG/SHORT",
            "entry_price": 63200.50,
            "stop_loss": 62900.00,
            "take_profit": 63600.00,
            "position_size_usd": 100,
            "confidence": 85,
            "reason": "Simple analysis reason"
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
            return self.simulate_decision(market_data)
                
        except Exception as e:
            print(f"❌ API error: {e}")
            return self.simulate_decision(market_data)
    
    def execute_simple_trade(self, decision):
        """Simple trade execution - $100 fixed"""
        try:
            pair = decision["pair"]
            direction = decision["direction"]
            entry_price = decision["entry_price"]
            
            # Calculate quantity for $100
            quantity = 100 / entry_price
            
            # Apply basic rounding
            quantity = round(quantity, 6)
            
            print(f"🔧 Trade Details:")
            print(f"   Pair: {pair}")
            print(f"   Direction: {direction}")
            print(f"   Entry: ${entry_price}")
            print(f"   Quantity: {quantity}")
            print(f"   Size: $100 fixed")
            
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
                "size_usd": 100
            }
            
            print(f"✅ TRADE EXECUTED: {direction} {pair}")
            print(f"   Entry: ${entry_price}")
            print(f"   SL: ${decision['stop_loss']}")
            print(f"   TP: ${decision['take_profit']}")
            print(f"   Reason: {decision['reason']}")
            
        except Exception as e:
            print(f"❌ Trade failed: {e}")
    
    def check_current_trade(self):
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
                self.close_simple_trade(exit_reason, current_price)
                
        except Exception as e:
            print(f"❌ Trade check error: {e}")
    
    def close_simple_trade(self, reason, exit_price):
        """Close current trade"""
        try:
            pair = self.active_trade["pair"]
            direction = self.active_trade["direction"]
            
            # Close opposite position
            if direction == "LONG":
                close_side = 'SELL'
            else:
                close_side = 'BUY'
            
            # Market order for instant close
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
            
            pnl_percent = (pnl / 100) * 100  # Based on $100
            
            print(f"🔚 TRADE CLOSED: {reason}")
            print(f"   Exit Price: ${exit_price}")
            print(f"   P&L: ${pnl:+.2f} ({pnl_percent:+.2f}%)")
            
            # Duration
            duration = time.time() - self.active_trade["entry_time"]
            print(f"   Duration: {duration/60:.1f} minutes")
            
            self.active_trade = None
            
        except Exception as e:
            print(f"❌ Close error: {e}")
    
    def simulate_decision(self, market_data):
        """AI API fail ရင် simulation သုံးမယ်"""
        # Simple simulation logic
        for pair, data in market_data.items():
            price = data['price']
            change = data.get('change_24h', 0)
            
            if change < -3:  # Oversold
                return {
                    "action": "TRADE",
                    "pair": pair,
                    "direction": "LONG",
                    "entry_price": round(price * 0.998, 4),
                    "stop_loss": round(price * 0.98, 4),
                    "take_profit": round(price * 1.02, 4),
                    "position_size_usd": 100,
                    "confidence": 75,
                    "reason": f"Simulation: {pair} oversold bounce"
                }
        
        return {
            "action": "SKIP",
            "confidence": 60,
            "reason": "Simulation: No clear signals"
        }
    
    def get_futures_market_data(self):
        """Futures market data"""
        market_data = {}
        
        for pair in self.available_pairs:
            try:
                ticker = self.binance.futures_symbol_ticker(symbol=pair)
                price = float(ticker['price'])
                
                klines = self.binance.futures_klines(
                    symbol=pair,
                    interval=Client.KLINE_INTERVAL_15MINUTE,
                    limit=10
                )
                
                closes = [float(k[4]) for k in klines]
                
                market_data[pair] = {
                    'price': price,
                    'change_24h': ((closes[-1] - closes[0]) / closes[0]) * 100,
                    'volume': float(klines[-1][5])
                }
                
            except Exception as e:
                print(f"❌ Data error for {pair}: {e}")
                continue
                
        return market_data

# 🚀 START BOT
if __name__ == "__main__":
    bot = SimpleFutureTrader(
        binance_api_key="YOUR_BINANCE_API",
        binance_secret="YOUR_BINANCE_SECRET",
        deepseek_api_key="YOUR_DEEPSEEK_API"
    )
    
    bot.run_simple_future()
