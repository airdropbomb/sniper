import requests
import json
import time
from binance.client import Client

class $100DeepSeekAutoTrader:
    def __init__(self, binance_api_key, binance_secret, deepseek_api_key):
        self.binance = Client(binance_api_key, binance_secret)
        self.deepseek_key = deepseek_api_key
        
        # Trading parameters
        self.trade_capital = 100  # $100 per trade
        self.available_pairs = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "XRPUSDT"]
        self.active_trade = None  # One trade at a time
        
    def run_$100_autonomous(self):
        """$100 နဲ့ fully autonomous trading"""
        print("🚀 DEEPSEEK $100 AUTONOMOUS TRADING STARTED!")
        print("💵 Risk: $100 per trade")
        print("🤖 DeepSeek controls EVERYTHING - TP/SL/Entries")
        
        while True:
            try:
                # 1. Get market data for all pairs
                market_data = self.get_all_market_data()
                
                # 2. DeepSeek makes full decision
                decision = self.get_deepseek_trading_decision(market_data)
                
                # 3. Execute if confidence high enough
                if decision["action"] == "TRADE" and decision["confidence"] >= 70:
                    if not self.active_trade:  # No existing trade
                        print(f"🎯 AI EXECUTING: {decision['pair']} {decision['direction']}")
                        self.execute_autonomous_trade(decision)
                    else:
                        print("⏳ Trade already active, waiting...")
                else:
                    print(f"⏸️ AI WAITING: {decision['reason']}")
                
                # 4. Check existing trade
                self.check_active_trade()
                
                time.sleep(300)  # 5 minutes
                
            except Exception as e:
                print(f"❌ Error: {e}")
                time.sleep(60)
    
    def get_deepseek_trading_decision(self, market_data):
        """DeepSeek ကို ဆုံးဖြတ်ခိုင်းမယ်"""
        
        prompt = f"""
        AUTONOMOUS $100 TRADING DECISION:
        
        TRADE CAPITAL: $100 (FIXED)
        AVAILABLE PAIRS: {self.available_pairs}
        CURRENT MARKET: {json.dumps(market_data, indent=2)}
        
        YOUR TASK: Make complete trading decision
        - Analyze all pairs
        - Choose BEST opportunity (or skip if none)
        - Set realistic Entry, Stop Loss, Take Profit
        - $100 position size
        - Provide detailed reasoning
        
        IMPORTANT: Stop Loss and Take Profit must be realistic based on current volatility.
        
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
            "reason": "BTC showing bullish RSI divergence at support with increasing volume. Stop Loss set below recent swing low, Take Profit at resistance level."
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
        
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers=headers,
            json=payload
        )
        
        result = response.json()
        content = result['choices'][0]['message']['content']
        
        # Extract JSON from response
        import re
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        return json.loads(json_match.group()) if json_match else {"action": "SKIP", "reason": "Invalid response"}
    
    def execute_autonomous_trade(self, decision):
        """DeepSeek ဆုံးဖြတ်ချက်အတိုင်း trade လုပ်မယ်"""
        try:
            pair = decision["pair"]
            direction = decision["direction"]
            entry_price = decision["entry_price"]
            
            # Calculate quantity based on $100
            quantity = 100 / entry_price
            
            if direction == "LONG":
                order = self.binance.order_limit_buy(
                    symbol=pair,
                    quantity=round(quantity, 6),  # BTC=0.00158, ETH=0.029, etc.
                    price=str(entry_price)
                )
            else:  # SHORT
                order = self.binance.order_limit_sell(
                    symbol=pair,
                    quantity=round(quantity, 6),
                    price=str(entry_price)
                )
            
            # Save active trade info
            self.active_trade = {
                "pair": pair,
                "direction": direction,
                "entry_price": entry_price,
                "stop_loss": decision["stop_loss"],
                "take_profit": decision["take_profit"],
                "quantity": quantity,
                "order_id": order['orderId']
            }
            
            print(f"✅ TRADE EXECUTED: {direction} {pair}")
            print(f"   Entry: ${entry_price}, SL: ${decision['stop_loss']}, TP: ${decision['take_profit']}")
            print(f"   Reason: {decision['reason']}")
            
        except Exception as e:
            print(f"❌ Trade execution failed: {e}")
    
    def check_active_trade(self):
        """Active trade ရှိမရှိစစ်ပြီး TP/SL check လုပ်မယ်"""
        if not self.active_trade:
            return
            
        try:
            pair = self.active_trade["pair"]
            ticker = self.binance.get_symbol_ticker(symbol=pair)
            current_price = float(ticker['price'])
            
            sl = self.active_trade["stop_loss"]
            tp = self.active_trade["take_profit"]
            
            # Check if stop loss or take profit hit
            if (self.active_trade["direction"] == "LONG" and current_price <= sl) or \
               (self.active_trade["direction"] == "SHORT" and current_price >= sl):
                self.close_trade("STOP LOSS")
                
            elif (self.active_trade["direction"] == "LONG" and current_price >= tp) or \
                 (self.active_trade["direction"] == "SHORT" and current_price <= tp):
                self.close_trade("TAKE PROFIT")
                
        except Exception as e:
            print(f"❌ Trade check error: {e}")
    
    def close_trade(self, reason):
        """Trade ကိုပိတ်မယ်"""
        try:
            self.binance.cancel_order(
                symbol=self.active_trade["pair"],
                orderId=self.active_trade["order_id"]
            )
            
            print(f"🔚 TRADE CLOSED: {reason}")
            print(f"   P&L: Calculating...")
            
            self.active_trade = None  # Reset
            
        except Exception as e:
            print(f"❌ Trade close error: {e}")

    def get_all_market_data(self):
        """All pairs ရဲ့ market data ကိုရမယ်"""
        market_data = {}
        
        for pair in self.available_pairs:
            try:
                # Price
                ticker = self.binance.get_symbol_ticker(symbol=pair)
                price = float(ticker['price'])
                
                # KLines for analysis
                klines = self.binance.get_klines(
                    symbol=pair,
                    interval=Client.KLINE_INTERVAL_15MINUTE,
                    limit=20
                )
                
                closes = [float(k[4]) for k in klines]
                highs = [float(k[2]) for k in klines]
                lows = [float(k[3]) for k in klines]
                
                market_data[pair] = {
                    'price': price,
                    'high_24h': max(highs),
                    'low_24h': min(lows),
                    'volume': float(klines[-1][5]),
                    'change_24h': ((closes[-1] - closes[0]) / closes[0]) * 100
                }
                
            except Exception as e:
                print(f"❌ Market data error for {pair}: {e}")
                continue
                
        return market_data

# 🚀 START THE BOT
if __name__ == "__main__":
    bot = $100DeepSeekAutoTrader(
        binance_api_key="YOUR_BINANCE_API",
        binance_secret="YOUR_BINANCE_SECRET", 
        deepseek_api_key="YOUR_DEEPSEEK_API"
    )
    
    bot.run_$100_autonomous()
