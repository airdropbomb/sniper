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

class ScalpingFutureTrader:
    def __init__(self):
        # Load config from .env file
        self.binance_api_key = os.getenv('BINANCE_API_KEY')
        self.binance_secret = os.getenv('BINANCE_SECRET_KEY')
        self.deepseek_key = os.getenv('DEEPSEEK_API_KEY')
        
        # SCALPING parameters
        self.trade_size_usd = 100
        self.leverage = 10
        self.risk_percentage = 1.0
        self.scalp_take_profit = 0.008  # 0.8% for scalping
        self.scalp_stop_loss = 0.005    # 0.5% for scalping
        
        # Initialize Binance client
        self.binance = Client(self.binance_api_key, self.binance_secret)
        
        self.available_pairs = ["ETHUSDT", "SOLUSDT", "ADAUSDT"]
        self.active_trade = None
        
        print("⚡ SCALPING BOT ACTIVATED!")
        print(f"💵 Trade Size: ${self.trade_size_usd}")
        print(f"📈 Leverage: {self.leverage}x")
        print(f"🎯 Take Profit: {self.scalp_take_profit*100}%")
        print(f"🛡️ Stop Loss: {self.scalp_stop_loss*100}%")
        
        self.validate_config()
        self.setup_futures()
    
    def validate_config(self):
        """Check API keys"""
        if not all([self.binance_api_key, self.binance_secret, self.deepseek_key]):
            print("❌ Missing API keys in .env file!")
            return False
        print("✅ Configuration loaded successfully!")
        return True
    
    def setup_futures(self):
        """Setup futures trading"""
        try:
            for pair in self.available_pairs:
                self.binance.futures_change_leverage(
                    symbol=pair,
                    leverage=self.leverage
                )
            print("✅ Futures setup completed!")
        except Exception as e:
            print(f"❌ Futures setup failed: {e}")
    
    def run_scalping(self):
        """Scalping trading loop"""
        print("🚀 SCALPING BOT STARTED!")
        
        # Run debug first
        self.debug_why_no_trades()
        
        while True:
            try:
                # 1. Get market data
                market_data = self.get_detailed_market_data()
                
                # 2. Get AI decision for each pair
                for pair in self.available_pairs:
                    if self.active_trade:
                        break  # Only one trade at a time for scalping
                    
                    pair_data = {pair: market_data[pair]}
                    decision = self.get_scalping_decision(pair_data)
                    
                    # 3. Execute if good for scalping
                    if decision["action"] == "TRADE" and decision["confidence"] >= 65:
                        print(f"🎯 SCALPING: {decision['pair']} {decision['direction']}")
                        self.execute_scalping_trade(decision)
                
                # 4. Check current trade
                self.check_scalping_trade()
                
                time.sleep(60)  # 1 minute for scalping
                
            except Exception as e:
                print(f"❌ Error: {e}")
                time.sleep(30)
    
    def get_scalping_decision(self, market_data):
        """Scalping-optimized AI decision"""
        pair = list(market_data.keys())[0]
        data = market_data[pair]
        price = data['price']
        
        prompt = f"""
        SCALPING TRADING ANALYSIS FOR {pair}:
        
        CURRENT PRICE: ${price}
        24H CHANGE: {data.get('change_24h', 0):.2f}%
        VOLUME RATIO: {data.get('volume_ratio', 1):.2f}x
        
        SCALPING STRATEGY:
        - Look for quick 0.5-1% moves
        - Short-term momentum
        - 5-30 minute holds
        - Tight stop losses
        
        Analyze for SCALPING opportunities only. Even small moves are acceptable.
        
        RESPONSE (JSON):
        {{
            "action": "TRADE/SKIP",
            "pair": "{pair}",
            "direction": "LONG/SHORT",
            "entry_price": {price},
            "stop_loss": number,
            "take_profit": number,
            "position_size_usd": {self.trade_size_usd},
            "confidence": 0-100,
            "reason": "Scalping analysis..."
        }}
        """
        
        try:
            headers = {
                "Authorization": f"Bearer {self.deepseek_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": 500
            }
            
            response = requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=20
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    decision = json.loads(json_match.group())
                    print(f"🤖 AI Decision: {decision['action']} ({decision['confidence']}%)")
                    return decision
            
        except Exception as e:
            print(f"❌ AI API Error: {e}")
        
        # Fallback to scalping logic
        return self.get_scalping_fallback(market_data)
    
    def get_scalping_fallback(self, market_data):
        """Scalping fallback logic"""
        pair = list(market_data.keys())[0]
        data = market_data[pair]
        price = data['price']
        change = data.get('change_24h', 0)
        
        # More sensitive scalping triggers
        if abs(change) > 0.3:  # Only 0.3% move needed
            if change < 0:
                return {
                    "action": "TRADE",
                    "pair": pair,
                    "direction": "LONG",
                    "entry_price": price,
                    "stop_loss": round(price * (1 - self.scalp_stop_loss), 4),
                    "take_profit": round(price * (1 + self.scalp_take_profit), 4),
                    "position_size_usd": self.trade_size_usd,
                    "confidence": 70,
                    "reason": f"Scalp: {pair} dipped {change:.2f}%, quick bounce play"
                }
            else:
                return {
                    "action": "TRADE",
                    "pair": pair,
                    "direction": "SHORT", 
                    "entry_price": price,
                    "stop_loss": round(price * (1 + self.scalp_stop_loss), 4),
                    "take_profit": round(price * (1 - self.scalp_take_profit), 4),
                    "position_size_usd": self.trade_size_usd,
                    "confidence": 70,
                    "reason": f"Scalp: {pair} rose {change:.2f}%, quick pullback play"
                }
        
        # Even if flat, try a random scalping trade
        import random
        if random.random() > 0.7:  # 30% chance to trade even in flat market
            direction = "LONG" if random.random() > 0.5 else "SHORT"
            return {
                "action": "TRADE",
                "pair": pair,
                "direction": direction,
                "entry_price": price,
                "stop_loss": round(price * (1 - self.scalp_stop_loss), 4),
                "take_profit": round(price * (1 + self.scalp_take_profit), 4),
                "position_size_usd": self.trade_size_usd,
                "confidence": 60,
                "reason": f"Scalp: Testing {direction} in flat market"
            }
        
        return {
            "action": "SKIP", 
            "confidence": 50,
            "reason": f"Scalp: {pair} too flat for scalping"
        }

    def execute_scalping_trade(self, decision):
        """Execute scalping trade - FIXED INDENTATION"""
        try:
            pair = decision["pair"]
            direction = decision["direction"]
            
            # Get current price
            ticker = self.binance.futures_symbol_ticker(symbol=pair)
            current_price = float(ticker['price'])
            
            # Calculate quantity
            quantity = self.trade_size_usd / current_price
            if pair == "ADAUSDT":
                quantity = int(quantity)
            else:
                quantity = round(quantity, 3)
            
            print(f"⚡ SCALPING EXECUTION:")
            print(f"   {direction} {quantity} {pair} @ Market")
            
            # MARKET ENTRY
            if direction == "LONG":
                entry_order = self.binance.futures_create_order(
                    symbol=pair,
                    side='BUY',
                    type='MARKET',
                    quantity=quantity
                )
                actual_entry = float(entry_order['avgPrice'])
            else:
                entry_order = self.binance.futures_create_order(
                    symbol=pair,
                    side='SELL', 
                    type='MARKET',
                    quantity=quantity
                )
                actual_entry = float(entry_order['avgPrice'])
            
            print(f"✅ ENTRY: {actual_entry}")
            
            # TP/SL orders - FIX timeInForce
            stop_loss = decision["stop_loss"]
            take_profit = decision["take_profit"]
            
            if direction == "LONG":
                # STOP LOSS
                self.binance.futures_create_order(
                    symbol=pair,
                    side='SELL',
                    type='STOP_MARKET',
                    quantity=quantity,
                    stopPrice=str(stop_loss),
                    timeInForce='GTC',  # ✅ ADD THIS
                    reduceOnly=True
                )
                # TAKE PROFIT
                self.binance.futures_create_order(
                    symbol=pair,
                    side='SELL',
                    type='LIMIT',
                    quantity=quantity,
                    price=str(take_profit),
                    timeInForce='GTC',  # ✅ ADD THIS
                    reduceOnly=True
                )
            else:
                # STOP LOSS
                self.binance.futures_create_order(
                    symbol=pair,
                    side='BUY',
                    type='STOP_MARKET',
                    quantity=quantity,
                    stopPrice=str(stop_loss),
                    timeInForce='GTC',  # ✅ ADD THIS
                    reduceOnly=True
                )
                # TAKE PROFIT
                self.binance.futures_create_order(
                    symbol=pair,
                    side='BUY',
                    type='LIMIT',
                    quantity=quantity,
                    price=str(take_profit),
                    timeInForce='GTC',  # ✅ ADD THIS
                    reduceOnly=True
                )
            
            self.active_trade = {
                "pair": pair,
                "direction": direction,
                "entry_price": actual_entry,
                "quantity": quantity,
                "entry_time": time.time()
            }
            
            print(f"🎯 SCALPING TRADE ACTIVE!")
            print(f"   SL: ${stop_loss}, TP: ${take_profit}")
            
        except Exception as e:
            print(f"❌ Scalping trade failed: {e}")

    def check_scalping_trade(self):
        """Check scalping trade status"""
        if not self.active_trade:
            return
        
        try:
            pair = self.active_trade["pair"]
            
            # Check if position still exists
            positions = self.binance.futures_position_information(symbol=pair)
            position = next((p for p in positions if float(p['positionAmt']) != 0), None)
            
            if not position:
                print("💰 SCALPING TRADE COMPLETED!")
                self.active_trade = None
                
        except Exception as e:
            print(f"❌ Trade check error: {e}")

    def debug_why_no_trades(self):
        """Debug why no trades are executing"""
        print("\n🔍 DEBUGGING SCALPING BOT...")
        print("=" * 50)
        
        market_data = self.get_detailed_market_data()
        
        for pair in self.available_pairs:
            print(f"\n📊 {pair}:")
            data = market_data[pair]
            print(f"   Price: ${data['price']}")
            print(f"   24h Change: {data['change_24h']:.2f}%")
            print(f"   Volume Ratio: {data['volume_ratio']:.2f}x")
            
            # Test AI decision
            pair_data = {pair: data}
            decision = self.get_scalping_decision(pair_data)
            
            print(f"   AI Decision: {decision['action']} ({decision['confidence']}%)")
            print(f"   Reason: {decision['reason']}")
            
            if decision['action'] == 'SKIP':
                print(f"   ❌ SKIPPED - {decision['reason']}")
            else:
                print(f"   ✅ WOULD TRADE - {decision['reason']}")

    def get_detailed_market_data(self):
        """Get market data"""
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
                volumes = [float(k[5]) for k in klines]
                
                current_volume = volumes[-1] if volumes else 0
                avg_volume = np.mean(volumes[-5:]) if len(volumes) >= 5 else current_volume
                
                market_data[pair] = {
                    'price': price,
                    'change_24h': ((closes[-1] - closes[0]) / closes[0]) * 100 if closes else 0,
                    'volume_ratio': current_volume / avg_volume if avg_volume > 0 else 1
                }
                
            except Exception as e:
                print(f"❌ Market data error for {pair}: {e}")
                continue
                
        return market_data

# 🚀 START SCALPING BOT
if __name__ == "__main__":
    try:
        bot = ScalpingFutureTrader()
        bot.run_scalping()
    except Exception as e:
        print(f"❌ Failed to start bot: {e}")
