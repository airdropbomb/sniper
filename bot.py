import requests
import json
import time
import re
from binance.client import Client

class FullyAutonomousFutureTrader:
    def __init__(self, binance_api_key, binance_secret, deepseek_api_key):
        self.binance = Client(binance_api_key, binance_secret)
        self.deepseek_key = deepseek_api_key
        
        self.trade_size_usd = 100  # Fixed $100
        self.available_pairs = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "XRPUSDT"]
        self.active_trade = None
    
    def run_fully_autonomous(self):
        """Fully autonomous - DeepSeek decides everything"""
        print("🚀 FULLY AUTONOMOUS FUTURES BOT STARTED!")
        print("🤖 DeepSeek controls ALL decisions:")
        print("   📊 Market Analysis")
        print("   ⏰ Entry Timing") 
        print("   🎯 Exit Points")
        print("   📈 Technical Decisions")
        print("   💵 $100 fixed size")
        
        while True:
            try:
                # 1. Get comprehensive market data
                market_data = self.get_detailed_market_data()
                
                # 2. DeepSeek analyzes and decides everything
                decision = self.get_deepseek_autonomous_decision(market_data)
                
                # 3. Execute DeepSeek's decision
                if decision["action"] == "TRADE" and decision["confidence"] >= 70:
                    if not self.active_trade:
                        print(f"🎯 DEEPSEEK EXECUTING: {decision['pair']} {decision['direction']}")
                        print(f"   Reason: {decision['reason']}")
                        self.execute_autonomous_trade(decision)
                    else:
                        print("⏳ Trade active, waiting for exit...")
                else:
                    print(f"⏸️ DEEPSEEK WAITING: {decision['reason']}")
                
                # 4. Check if should exit current trade
                self.check_autonomous_exit()
                
                time.sleep(300)  # 5 minutes between analysis
                
            except Exception as e:
                print(f"❌ Error: {e}")
                time.sleep(60)
    
    def get_deepseek_autonomous_decision(self, market_data):
        """DeepSeek က market analysis လုပ်ပြီး ဘာလုပ်ရမယ်ဆိုတာ ဆုံးဖြတ်မယ်"""
        
        prompt = f"""
        YOU ARE A FULLY AUTONOMOUS TRADING AI.
        
        CURRENT MARKET DATA FOR ANALYSIS:
        {json.dumps(market_data, indent=2)}
        
        AVAILABLE TRADING PAIRS: {self.available_pairs}
        TRADE SIZE: $100 FIXED (position_size_usd should always be 100)
        
        YOUR TASK: Analyze the market and make COMPLETE trading decisions:
        1. Technical Analysis of ALL pairs
        2. Identify the HIGHEST probability trade
        3. Determine EXACT entry price
        4. Set appropriate stop loss and take profit
        5. Assess risk/reward ratio
        6. Provide detailed technical reasoning
        
        TECHNICAL FACTORS TO ANALYZE:
        - Price trends and momentum
        - Support and resistance levels
        - RSI conditions (overbought/oversold)
        - Volume analysis
        - Market volatility
        - Risk management
        
        RESPONSE MUST BE JSON:
        {{
            "action": "TRADE/SKIP",
            "pair": "SYMBOL", 
            "direction": "LONG/SHORT",
            "entry_price": number,
            "stop_loss": number,
            "take_profit": number,
            "position_size_usd": 100,
            "confidence": 0-100,
            "reason": "Detailed technical analysis explaining your decision including: price levels, indicators, risk assessment, and expected price movement."
        }}
        
        Be specific in your reasoning. If skipping, explain why no good opportunities exist.
        """
        
        headers = {
            "Authorization": f"Bearer {self.deepseek_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,  # Low temperature for consistent decisions
            "max_tokens": 1500
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
                
                # Extract JSON from AI response
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    decision = json.loads(json_match.group())
                    
                    # Validate decision format
                    if self.validate_decision(decision):
                        return decision
                    else:
                        print("❌ Invalid decision format from AI")
                        return self.get_fallback_decision(market_data)
                else:
                    print("❌ No JSON in AI response")
                    return self.get_fallback_decision(market_data)
            else:
                print(f"❌ API error: {response.status_code}")
                return self.get_fallback_decision(market_data)
                
        except Exception as e:
            print(f"❌ API call failed: {e}")
            return self.get_fallback_decision(market_data)
    
    def validate_decision(self, decision):
        """Validate AI decision format"""
        required_fields = ["action", "pair", "direction", "entry_price", "stop_loss", "take_profit", "confidence", "reason"]
        return all(field in decision for field in required_fields)
    
    def get_fallback_decision(self, market_data):
        """AI API fail ရင် backup analysis"""
        print("⚠️ Using fallback analysis...")
        
        # Simple technical analysis fallback
        for pair, data in market_data.items():
            price = data['price']
            change = data.get('change_24h', 0)
            rsi = data.get('rsi', 50)
            
            # Oversold bounce opportunity
            if rsi < 35 and change < -2:
                return {
                    "action": "TRADE",
                    "pair": pair,
                    "direction": "LONG", 
                    "entry_price": round(price * 0.998, 4),
                    "stop_loss": round(price * 0.98, 4),
                    "take_profit": round(price * 1.02, 4),
                    "position_size_usd": 100,
                    "confidence": 70,
                    "reason": f"Fallback: {pair} oversold with RSI {rsi}, potential bounce from support"
                }
            
            # Overbought rejection opportunity  
            elif rsi > 65 and change > 2:
                return {
                    "action": "TRADE",
                    "pair": pair,
                    "direction": "SHORT",
                    "entry_price": round(price * 1.002, 4),
                    "stop_loss": round(price * 1.02, 4),
                    "take_profit": round(price * 0.98, 4),
                    "position_size_usd": 100,
                    "confidence": 70,
                    "reason": f"Fallback: {pair} overbought with RSI {rsi}, potential rejection from resistance"
                }
        
        return {
            "action": "SKIP",
            "confidence": 50,
            "reason": "Fallback: No clear technical signals detected"
        }
    
    def execute_autonomous_trade(self, decision):
        """DeepSeek ဆုံးဖြတ်ချက်အတိုင်း trade လုပ်မယ်"""
        try:
            pair = decision["pair"]
            direction = decision["direction"]
            entry_price = decision["entry_price"]
            
            # Calculate quantity for $100
            quantity = 100 / entry_price
            quantity = round(quantity, 6)
            
            print(f"🔧 DEEPSEEK TRADE EXECUTION:")
            print(f"   Pair: {pair}")
            print(f"   Direction: {direction}")
            print(f"   Entry: ${entry_price}")
            print(f"   Stop Loss: ${decision['stop_loss']}") 
            print(f"   Take Profit: ${decision['take_profit']}")
            print(f"   Quantity: {quantity}")
            print(f"   Confidence: {decision['confidence']}%")
            
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
                "reason": decision["reason"]
            }
            
            print(f"✅ DEEPSEEK TRADE EXECUTED!")
            
        except Exception as e:
            print(f"❌ Trade execution failed: {e}")
    
    def check_autonomous_exit(self):
        """Check if should exit based on DeepSeek's levels"""
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
            
            pnl_percent = (pnl / 100) * 100
            
            print(f"🔚 DEEPSEEK TRADE CLOSED: {reason}")
            print(f"   Exit Price: ${exit_price}")
            print(f"   P&L: ${pnl:+.2f} ({pnl_percent:+.2f}%)")
            print(f"   Original Reason: {self.active_trade['reason']}")
            
            # Duration
            duration = time.time() - self.active_trade["entry_time"]
            print(f"   Duration: {duration/60:.1f} minutes")
            
            self.active_trade = None
            
        except Exception as e:
            print(f"❌ Close error: {e}")
    
    def get_detailed_market_data(self):
        """Comprehensive market data for DeepSeek analysis"""
        market_data = {}
        
        for pair in self.available_pairs:
            try:
                # Current price
                ticker = self.binance.futures_symbol_ticker(symbol=pair)
                price = float(ticker['price'])
                
                # Historical data for analysis
                klines = self.binance.futures_klines(
                    symbol=pair,
                    interval=Client.KLINE_INTERVAL_15MINUTE,
                    limit=50
                )
                
                closes = [float(k[4]) for k in klines]
                highs = [float(k[2]) for k in klines]
                lows = [float(k[3]) for k in klines]
                volumes = [float(k[5]) for k in klines]
                
                # Calculate technical indicators
                rsi = self.calculate_rsi(closes)
                current_volume = volumes[-1] if volumes else 0
                avg_volume = np.mean(volumes[-10:]) if len(volumes) >= 10 else current_volume
                
                market_data[pair] = {
                    'price': price,
                    'high_24h': max(highs[-24:]) if len(highs) >= 24 else max(highs),
                    'low_24h': min(lows[-24:]) if len(lows) >= 24 else min(lows),
                    'volume': current_volume,
                    'volume_ratio': current_volume / avg_volume if avg_volume > 0 else 1,
                    'change_24h': ((closes[-1] - closes[0]) / closes[0]) * 100 if closes else 0,
                    'rsi': rsi,
                    'volatility': (max(highs[-10:]) - min(lows[-10:])) / closes[-1] * 100 if len(closes) >= 10 else 0
                }
                
            except Exception as e:
                print(f"❌ Market data error for {pair}: {e}")
                continue
                
        return market_data
    
    def calculate_rsi(self, prices, period=14):
        """Calculate RSI indicator"""
        if len(prices) < period + 1:
            return 50
            
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gains = np.convolve(gains, np.ones(period)/period, mode='valid')
        avg_losses = np.convolve(losses, np.ones(period)/period, mode='valid')
        
        rs = avg_gains / np.where(avg_losses == 0, 1, avg_losses)
        rsi = 100 - (100 / (1 + rs))
        
        return round(rsi[-1], 2) if len(rsi) > 0 else 50

# 🚀 START FULLY AUTONOMOUS BOT
if __name__ == "__main__":
    bot = FullyAutonomousFutureTrader(
        binance_api_key="YOUR_BINANCE_API",
        binance_secret="YOUR_BINANCE_SECRET",
        deepseek_api_key="YOUR_DEEPSEEK_API"
    )
    
    bot.run_fully_autonomous()
