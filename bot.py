import requests
import json
import time
import hmac
import hashlib
from binance.client import Client
from datetime import datetime

class DeepSeekTradingBot:
    def __init__(self, binance_api_key, binance_secret_key, deepseek_api_key):
        # Binance API Setup
        self.binance_client = Client(binance_api_key, binance_secret_key)
        
        # DeepSeek API Setup
        self.deepseek_api_key = deepseek_api_key
        self.deepseek_url = "https://api.deepseek.com/v1/chat/completions"
        
        # Trading Parameters
        self.symbol = "BTCUSDT"
        self.trade_amount = 0.001  # BTC amount per trade
        self.max_risk = 0.02  # 2% risk per trade
        
    def get_binance_data(self):
        """Get real-time market data from Binance"""
        try:
            # Current price
            ticker = self.binance_client.get_symbol_ticker(symbol=self.symbol)
            current_price = float(ticker['price'])
            
            # 15-minute KLines for technical analysis
            klines = self.binance_client.get_klines(
                symbol=self.symbol, 
                interval=Client.KLINE_INTERVAL_15MINUTE, 
                limit=50
            )
            
            # Calculate RSI
            closes = [float(k[4]) for k in klines]
            rsi = self.calculate_rsi(closes)
            
            # Support and Resistance
            support = min(closes[-20:]) * 0.999
            resistance = max(closes[-20:]) * 1.001
            
            market_data = {
                'symbol': self.symbol,
                'price': current_price,
                'rsi': rsi,
                'support': support,
                'resistance': resistance,
                'volume': float(klines[-1][5]),
                'timestamp': datetime.now().isoformat()
            }
            
            return market_data
            
        except Exception as e:
            print(f"Binance data error: {e}")
            return None
    
    def calculate_rsi(self, prices, period=14):
        """Calculate RSI indicator"""
        if len(prices) < period + 1:
            return 50
            
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
            else:
                losses.append(abs(change))
                
        if len(gains) < period or len(losses) < period:
            return 50
            
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100
            
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return round(rsi, 2)
    
    def get_deepseek_analysis(self, market_data):
        """Get trading analysis from DeepSeek AI"""
        try:
            prompt = f"""
            CRYPTO TRADING ANALYSIS REQUEST:
            
            SYMBOL: {market_data['symbol']}
            CURRENT PRICE: {market_data['price']}
            RSI (14): {market_data['rsi']}
            SUPPORT: {market_data['support']:.2f}
            RESISTANCE: {market_data['resistance']:.2f}
            VOLUME: {market_data['volume']:.2f}
            
            SCALPING STRATEGY (5-30 minutes hold):
            - Analyze current market condition
            - Identify entry/exit points
            - Assess risk/reward ratio
            
            RESPONSE FORMAT (JSON only):
            {{
                "action": "BUY/SELL/HOLD",
                "confidence": 0-100,
                "entry_price": number,
                "stop_loss": number, 
                "take_profit": number,
                "reason": "brief explanation",
                "timeframe": "expected hold duration"
            }}
            """
            
            headers = {
                "Authorization": f"Bearer {self.deepseek_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 500
            }
            
            response = requests.post(self.deepseek_url, headers=headers, json=payload)
            response.raise_for_status()
            
            ai_response = response.json()
            content = ai_response['choices'][0]['message']['content']
            
            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                trading_signal = json.loads(json_match.group())
                return trading_signal
            else:
                print("No JSON found in AI response")
                return None
                
        except Exception as e:
            print(f"DeepSeek API error: {e}")
            return None
    
    def execute_trade(self, signal, market_data):
        """Execute trade based on AI signal"""
        try:
            if signal['confidence'] < 70:
                print(f"❌ Low confidence: {signal['confidence']}% - Skipping trade")
                return False
            
            current_price = market_data['price']
            
            if signal['action'] == 'BUY':
                # Place buy order
                order = self.binance_client.order_limit_buy(
                    symbol=self.symbol,
                    quantity=self.trade_amount,
                    price=str(current_price)
                )
                print(f"✅ BUY order placed: {self.trade_amount} {self.symbol} at {current_price}")
                
                # Set stop loss and take profit
                self.place_stop_loss(signal['stop_loss'])
                self.place_take_profit(signal['take_profit'])
                
            elif signal['action'] == 'SELL':
                # Place sell order  
                order = self.binance_client.order_limit_sell(
                    symbol=self.symbol,
                    quantity=self.trade_amount, 
                    price=str(current_price)
                )
                print(f"✅ SELL order placed: {self.trade_amount} {self.symbol} at {current_price}")
                
            else:  # HOLD
                print(f"⚡ HOLD signal - Reason: {signal['reason']}")
                return False
                
            return True
            
        except Exception as e:
            print(f"Trade execution error: {e}")
            return False
    
    def place_stop_loss(self, stop_price):
        """Place stop loss order"""
        try:
            order = self.binance_client.create_order(
                symbol=self.symbol,
                side=Client.SIDE_SELL,
                type=Client.ORDER_TYPE_STOP_LOSS_LIMIT,
                quantity=self.trade_amount,
                price=str(stop_price * 0.998),  # Slightly below stop
                stopPrice=str(stop_price),
                timeInForce=Client.TIME_IN_FORCE_GTC
            )
            print(f"🛡️ Stop loss set at: {stop_price}")
        except Exception as e:
            print(f"Stop loss error: {e}")
    
    def place_take_profit(self, take_profit_price):
        """Place take profit order"""
        try:
            order = self.binance_client.create_order(
                symbol=self.symbol,
                side=Client.SIDE_SELL,
                type=Client.ORDER_TYPE_LIMIT,
                quantity=self.trade_amount,
                price=str(take_profit_price),
                timeInForce=Client.TIME_IN_FORCE_GTC
            )
            print(f"🎯 Take profit set at: {take_profit_price}")
        except Exception as e:
            print(f"Take profit error: {e}")
    
    def run_bot(self):
        """Main bot execution loop"""
        print("🚀 DeepSeek Trading Bot Started!")
        print("=" * 50)
        
        while True:
            try:
                # 1. Get market data
                print(f"\n📊 Fetching market data... {datetime.now().strftime('%H:%M:%S')}")
                market_data = self.get_binance_data()
                
                if not market_data:
                    time.sleep(60)
                    continue
                
                print(f"💰 {market_data['symbol']} Price: ${market_data['price']:.2f}")
                print(f"📈 RSI: {market_data['rsi']}")
                
                # 2. Get AI analysis
                print("🤖 Consulting DeepSeek AI...")
                signal = self.get_deepseek_analysis(market_data)
                
                if signal:
                    print(f"🎯 Signal: {signal['action']} (Confidence: {signal['confidence']}%)")
                    print(f"💡 Reason: {signal['reason']}")
                    
                    # 3. Execute trade
                    if signal['confidence'] >= 70:
                        self.execute_trade(signal, market_data)
                    else:
                        print("⏸️ Waiting for better opportunity...")
                
                # 4. Wait before next analysis
                print("💤 Waiting 5 minutes for next analysis...")
                time.sleep(300)  # 5 minutes
                
            except KeyboardInterrupt:
                print("\n🛑 Bot stopped by user")
                break
            except Exception as e:
                print(f"❌ Bot error: {e}")
                time.sleep(60)

# 🔑 Configuration and Initialization
if __name__ == "__main__":
    # API Keys (Replace with your actual keys)
    BINANCE_API_KEY = "your_binance_api_key_here"
    BINANCE_SECRET_KEY = "your_binance_secret_key_here" 
    DEEPSEEK_API_KEY = "your_deepseek_api_key_here"
    
    # Create and run bot
    bot = DeepSeekTradingBot(
        binance_api_key=BINANCE_API_KEY,
        binance_secret_key=BINANCE_SECRET_KEY,
        deepseek_api_key=DEEPSEEK_API_KEY
    )
    
    # Start trading
    bot.run_bot()
