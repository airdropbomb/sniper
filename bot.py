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

class MultiPairScalpingTrader:
    def __init__(self):
        # Load config from .env file
        self.binance_api_key = os.getenv('BINANCE_API_KEY')
        self.binance_secret = os.getenv('BINANCE_SECRET_KEY')
        self.deepseek_key = os.getenv('DEEPSEEK_API_KEY')
        
        # SCALPING parameters
        self.trade_size_usd = 150  # Increased for high-priced pairs
        self.leverage = 10
        self.risk_percentage = 1.0
        self.scalp_take_profit = 0.008  # 0.8% for scalping
        self.scalp_stop_loss = 0.005    # 0.5% for scalping
        
        # Multi-pair parameters
        self.max_concurrent_trades = 3
        self.available_pairs = []
        self.active_trades = {}  # Dictionary to track multiple trades
        self.blacklisted_pairs = ["BTCUSDT"]  # BTC ကိုထည့်မထားဘူး
        
        # Precision settings for different pairs
        self.quantity_precision = {}
        self.price_precision = {}
        
        # Auto pair selection parameters
        self.pair_rotation_hours = 6
        self.last_rotation_time = 0
        
        # Initialize Binance client
        self.binance = Client(self.binance_api_key, self.binance_secret)
        
        print("🤖 MULTI-PAIR SCALPING BOT ACTIVATED!")
        print(f"💵 Trade Size: ${self.trade_size_usd} per trade")
        print(f"📈 Max Concurrent Trades: {self.max_concurrent_trades}")
        print(f"🎯 Take Profit: {self.scalp_take_profit*100}%")
        print(f"🛡️ Stop Loss: {self.scalp_stop_loss*100}%")
        print(f"🚫 Blacklisted: {self.blacklisted_pairs}")
        
        self.validate_config()
        self.setup_futures()
        self.load_symbol_precision()
    
    def validate_config(self):
        """Check API keys"""
        if not all([self.binance_api_key, self.binance_secret, self.deepseek_key]):
            print("❌ Missing API keys in .env file!")
            return False
        
        # Test Binance connection
        try:
            self.binance.futures_exchange_info()
            print("✅ Binance connection successful!")
        except Exception as e:
            print(f"❌ Binance connection failed: {e}")
            return False
            
        print("✅ Configuration loaded successfully!")
        return True
    
    def load_symbol_precision(self):
        """Load quantity and price precision for all trading pairs"""
        try:
            exchange_info = self.binance.futures_exchange_info()
            for symbol in exchange_info['symbols']:
                pair = symbol['symbol']
                
                # Get quantity precision from LOT_SIZE filter
                for f in symbol['filters']:
                    if f['filterType'] == 'LOT_SIZE':
                        step_size = f['stepSize']
                        # Calculate precision from step size
                        if '1' in step_size:
                            qty_precision = 0
                        else:
                            qty_precision = len(step_size.split('.')[1].rstrip('0'))
                        self.quantity_precision[pair] = qty_precision
                    
                    # Get price precision from PRICE_FILTER
                    elif f['filterType'] == 'PRICE_FILTER':
                        tick_size = f['tickSize']
                        if '1' in tick_size:
                            price_precision = 0
                        else:
                            price_precision = len(tick_size.split('.')[1].rstrip('0'))
                        self.price_precision[pair] = price_precision
            
            print("✅ Symbol precision loaded for all pairs")
        except Exception as e:
            print(f"❌ Error loading symbol precision: {e}")
    
    def get_quantity(self, pair, price):
        """FIXED - Ensure minimum trade size"""
        try:
            # Calculate base quantity
            base_quantity = self.trade_size_usd / price
            print(f"🔢 {pair} base quantity: {base_quantity}")
            
            # Apply precision based on pair
            precision = self.quantity_precision.get(pair, 2)
            
            # Round to correct precision
            quantity = round(base_quantity, precision)
            
            # For pairs that require integer quantities
            if precision == 0:
                quantity = int(quantity)
            
            # Calculate actual trade value
            trade_value = quantity * price
            
            # If trade value is too small, adjust quantity upward
            if trade_value < self.trade_size_usd * 0.8:  # If less than 80% of target
                # Calculate minimum quantity to reach target
                min_quantity = self.trade_size_usd / price
                quantity = round(min_quantity, precision)
                if precision == 0:
                    quantity = int(quantity)
                
                # Recalculate trade value
                trade_value = quantity * price
                print(f"🔄 Adjusted {pair} quantity to {quantity} (${trade_value:.2f})")
            
            # Ensure minimum quantity requirement
            min_qty = self.get_minimum_quantity(pair)
            if quantity < min_qty:
                quantity = min_qty
                trade_value = quantity * price
                print(f"📏 Using minimum quantity {quantity} for {pair} (${trade_value:.2f})")
            
            print(f"💰 FINAL: {quantity} {pair} = ${trade_value:.2f}")
            
            return quantity
            
        except Exception as e:
            print(f"❌ Quantity calculation error for {pair}: {e}")
            # Fallback to minimum quantity
            return self.get_minimum_quantity(pair)
    
    def get_minimum_quantity(self, pair):
        """Get minimum quantity for a pair based on Binance requirements"""
        min_quantities = {
            'ADAUSDT': 1, 'XRPUSDT': 1, 'DOGEUSDT': 1, 'TRXUSDT': 1,
            'ETHUSDT': 0.001, 'BNBUSDT': 0.01, 'SOLUSDT': 0.01,
            'AVAXUSDT': 0.1, 'MATICUSDT': 1, 'DOTUSDT': 0.1,
            'LINKUSDT': 0.1, 'LTCUSDT': 0.01, 'ATOMUSDT': 0.1
        }
        return min_quantities.get(pair, 0.01)
    
    def format_price(self, pair, price):
        """Format price according to symbol precision"""
        precision = self.price_precision.get(pair, 4)
        return round(price, precision)
    
    def setup_futures(self):
        """Setup futures trading for initial pairs"""
        try:
            # Initial pairs without BTC
            initial_pairs = ["ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT", "XRPUSDT", "AVAXUSDT"]
            for pair in initial_pairs:
                try:
                    self.binance.futures_change_leverage(
                        symbol=pair,
                        leverage=self.leverage
                    )
                    print(f"✅ Leverage set for {pair}")
                except Exception as e:
                    print(f"⚠️ Leverage setup failed for {pair}: {e}")
            print("✅ Futures setup completed!")
        except Exception as e:
            print(f"❌ Futures setup failed: {e}")
    
    def get_ai_recommended_pairs(self):
        """AI ကနေ BTC မပါတဲ့ scalping pairs တွေရွေးခိုင်းခြင်း"""
        print("🤖 AI က BTC မပါတဲ့ scalping pairs တွေရွေးနေပါတယ်...")
        
        prompt = """
        BINANCE FUTURES SCALPING PAIR RECOMMENDATIONS (EXCLUDE BTCUSDT):
        
        SCALPING CRITERIA:
        - High liquidity but NOT BTCUSDT
        - Good volatility (2-10% daily moves)
        - Tight spreads
        - Popular altcoin pairs
        - USDT pairs only
        - Suitable for 0.5-1% quick scalps
        - Exclude BTC completely
        
        Recommend 6-10 best altcoin pairs for scalping from Binance futures.
        Focus on ETH, BNB, SOL, ADA, XRP, DOT, MATIC, AVAX, LINK, etc.
        
        RESPONSE (JSON only):
        {
            "recommended_pairs": ["ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT", ...],
            "reason": "These altcoin pairs have high liquidity and volatility suitable for scalping, excluding BTC",
            "expected_volatility": "high/medium",
            "market_sentiment": "bullish/bearish/neutral"
        }
        """
        
        try:
            headers = {
                "Authorization": f"Bearer {self.deepseek_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
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
                    recommendation = json.loads(json_match.group())
                    pairs = recommendation.get("recommended_pairs", [])
                    
                    # Remove BTC if AI accidentally includes it
                    pairs = [p for p in pairs if p != "BTCUSDT"]
                    
                    print(f"✅ AI Recommended Pairs (No BTC): {pairs}")
                    print(f"📝 Reason: {recommendation.get('reason', '')}")
                    
                    # Validate if pairs exist in Binance
                    valid_pairs = self.validate_ai_pairs(pairs)
                    return valid_pairs
            
        except Exception as e:
            print(f"❌ AI pair selection error: {e}")
        
        # Fallback to default pairs without BTC
        fallback_pairs = ["ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT", "XRPUSDT", "AVAXUSDT", "MATICUSDT"]
        print(f"🔄 Using fallback pairs (No BTC): {fallback_pairs}")
        return fallback_pairs
    
    def validate_ai_pairs(self, ai_pairs):
        """AI ရွေးတဲ့ pairs တွေ Binance မှာရှိမရှိစစ်ဆေးခြင်း"""
        valid_pairs = []
        
        try:
            # Get all available futures pairs from Binance
            exchange_info = self.binance.futures_exchange_info()
            all_symbols = [symbol['symbol'] for symbol in exchange_info['symbols']]
            
            for pair in ai_pairs:
                if pair in all_symbols and pair not in self.blacklisted_pairs:
                    # Check if pair is trading and has required leverage
                    for symbol in exchange_info['symbols']:
                        if symbol['symbol'] == pair and symbol['status'] == 'TRADING':
                            valid_pairs.append(pair)
                            print(f"✅ {pair} is available for trading")
                            break
                    else:
                        print(f"⚠️ {pair} exists but not trading")
                else:
                    print(f"❌ {pair} not available or blacklisted")
        
        except Exception as e:
            print(f"❌ Pair validation error: {e}")
            # Fallback to first 8 AI pairs assuming they're valid
            return ai_pairs[:8]
        
        print(f"🎯 Final Validated Pairs: {valid_pairs}")
        return valid_pairs[:10]  # Maximum 10 pairs for selection pool
    
    def rotate_pairs_based_on_performance(self):
        """စျေးကွက်အခြေအနေအရ pairs တွေကိုလည်ပတ်ရွေးချယ်ခြင်း"""
        print("🔄 Rotating pairs based on current market conditions...")
        
        market_condition_prompt = """
        Analyze current crypto market and recommend best scalping pairs for NEXT 6 HOURS.
        EXCLUDE BTCUSDT completely - focus only on altcoins.
        
        Consider:
        - Altcoin market trend vs BTC
        - Sector rotation (AI, DeFi, Gaming, etc.)
        - Volatility opportunities in alts
        - News and events affecting altcoins
        - Technical setups in altcoins
        
        Focus on altcoin pairs with imminent breakout/breakdown potential for 0.5-1% scalps.
        
        RESPONSE (JSON):
        {
            "market_condition": "altcoin_season/consolidating/volatile",
            "recommended_pairs": ["ETHUSDT", "BNBUSDT", "SOLUSDT", ...],
            "timeframe": "next_6_hours",
            "strategy": "Focus on AI sector altcoins",
            "risk_level": "medium/high",
            "key_opportunities": "ETH breaking resistance, SOL momentum play"
        }
        """
        
        try:
            headers = {
                "Authorization": f"Bearer {self.deepseek_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": market_condition_prompt}],
                "temperature": 0.4,
                "max_tokens": 600
            }
            
            response = requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=25
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    market_analysis = json.loads(json_match.group())
                    new_pairs = market_analysis.get("recommended_pairs", [])
                    
                    # Remove BTC if included
                    new_pairs = [p for p in new_pairs if p != "BTCUSDT"]
                    
                    if new_pairs:
                        valid_pairs = self.validate_ai_pairs(new_pairs)
                        if valid_pairs:
                            old_pairs = self.available_pairs.copy()
                            self.available_pairs = valid_pairs
                            
                            # Setup leverage for new pairs
                            for pair in valid_pairs:
                                try:
                                    self.binance.futures_change_leverage(
                                        symbol=pair,
                                        leverage=self.leverage
                                    )
                                except Exception as e:
                                    print(f"⚠️ Leverage setup failed for {pair}: {e}")
                            
                            print(f"🔄 Successfully rotated pairs!")
                            print(f"   Old: {old_pairs}")
                            print(f"   New: {valid_pairs}")
                            print(f"📈 Market Condition: {market_analysis.get('market_condition', 'unknown')}")
                            print(f"🎯 Strategy: {market_analysis.get('strategy', '')}")
                            return True
        
        except Exception as e:
            print(f"❌ Pair rotation error: {e}")
        
        return False
    
    def auto_rotate_pairs(self):
        """Auto rotate pairs based on time interval"""
        current_time = time.time()
        
        # Rotate every 6 hours or if no pairs available
        if (current_time - self.last_rotation_time > self.pair_rotation_hours * 3600 or 
            not self.available_pairs):
            
            print(f"🕒 Time for pair rotation...")
            success = self.rotate_pairs_based_on_performance()
            
            if success:
                self.last_rotation_time = current_time
            else:
                # If rotation fails, get basic AI recommendation
                self.available_pairs = self.get_ai_recommended_pairs()
                self.last_rotation_time = current_time
    
    def get_detailed_market_data(self):
        """Get market data for all active pairs"""
        market_data = {}
        
        if not self.available_pairs:
            print("⚠️ No pairs available, getting new pairs...")
            self.available_pairs = self.get_ai_recommended_pairs()
        
        for pair in self.available_pairs:
            try:
                # Skip if this pair already has active trade
                if pair in self.active_trades:
                    continue
                    
                # Get current price
                ticker = self.binance.futures_symbol_ticker(symbol=pair)
                price = float(ticker['price'])
                
                # Get klines for analysis
                klines = self.binance.futures_klines(
                    symbol=pair,
                    interval=Client.KLINE_INTERVAL_15MINUTE,
                    limit=20
                )
                
                if len(klines) > 0:
                    closes = [float(k[4]) for k in klines]
                    volumes = [float(k[5]) for k in klines]
                    highs = [float(k[2]) for k in klines]
                    lows = [float(k[3]) for k in klines]
                    
                    # Calculate metrics
                    current_volume = volumes[-1] if volumes else 0
                    avg_volume = np.mean(volumes[-10:]) if len(volumes) >= 10 else current_volume
                    
                    # Price change calculations
                    price_change_1h = ((closes[-1] - closes[-4]) / closes[-4]) * 100 if len(closes) >= 4 else 0
                    price_change_4h = ((closes[-1] - closes[-16]) / closes[-16]) * 100 if len(closes) >= 16 else 0
                    
                    # Volatility (ATR-like calculation)
                    true_ranges = []
                    for i in range(1, min(14, len(klines))):
                        high = highs[i]
                        low = lows[i]
                        prev_close = closes[i-1]
                        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
                        true_ranges.append(tr)
                    
                    atr = np.mean(true_ranges) if true_ranges else 0
                    volatility = (atr / price) * 100 if price > 0 else 0
                    
                    market_data[pair] = {
                        'price': price,
                        'change_1h': price_change_1h,
                        'change_4h': price_change_4h,
                        'volume_ratio': current_volume / avg_volume if avg_volume > 0 else 1,
                        'volatility': volatility,
                        'high_1h': max(highs[-4:]) if len(highs) >= 4 else price,
                        'low_1h': min(lows[-4:]) if len(lows) >= 4 else price
                    }
                
            except Exception as e:
                print(f"❌ Market data error for {pair}: {e}")
                continue
                
        return market_data
    
    def get_scalping_decision(self, market_data):
        """Scalping-optimized AI decision for both LONG and SHORT"""
        pair = list(market_data.keys())[0]
        data = market_data[pair]
        price = data['price']
        
        prompt = f"""
        URGENT SCALPING ANALYSIS FOR {pair} (ALTCOIN):
        
        CURRENT MARKET DATA:
        - Price: ${price}
        - 1H Change: {data.get('change_1h', 0):.2f}%
        - 4H Change: {data.get('change_4h', 0):.2f}%
        - Volume Ratio: {data.get('volume_ratio', 1):.2f}x
        - Volatility: {data.get('volatility', 0):.2f}%
        - 1H Range: ${data.get('low_1h', price):.2f} - ${data.get('high_1h', price):.2f}
        
        SCALPING STRATEGY - BOTH LONG & SHORT:
        LONG opportunities:
        - Price near support levels ({data.get('low_1h', price):.2f})
        - Oversold conditions (recent dip)
        - Positive momentum reversal
        - High volume buying
        
        SHORT opportunities:  
        - Price near resistance levels ({data.get('high_1h', price):.2f})
        - Overbought conditions (recent pump)
        - Negative momentum reversal  
        - High volume selling
        
        Analyze for IMMEDIATE scalping entry within next 1-5 candles.
        Recommend SHORT if bearish signals are stronger than bullish.
        
        RESPONSE (JSON only):
        {{
            "action": "TRADE/SKIP",
            "pair": "{pair}",
            "direction": "LONG/SHORT",
            "entry_price": {price},
            "stop_loss": number,
            "take_profit": number,
            "position_size_usd": {self.trade_size_usd},
            "confidence": 0-100,
            "timeframe": "5-30min",
            "reason": "Specific LONG/SHORT technical reason...",
            "urgency": "high/medium/low"
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
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    decision = json.loads(json_match.group())
                    print(f"🤖 {pair}: {decision['action']} ({decision['confidence']}% confidence)")
                    if decision['action'] == 'TRADE':
                        print(f"   📈 Direction: {decision['direction']}")
                        print(f"   🎯 Reason: {decision['reason']}")
                        print(f"   ⚡ Urgency: {decision.get('urgency', 'medium')}")
                    return decision
            
        except Exception as e:
            print(f"❌ AI API Error for {pair}: {e}")
        
        # Fallback to scalping logic
        return self.get_scalping_fallback(market_data)
    
    def get_scalping_fallback(self, market_data):
        """Scalping fallback logic with both LONG and SHORT"""
        pair = list(market_data.keys())[0]
        data = market_data[pair]
        price = data['price']
        change_1h = data.get('change_1h', 0)
        volatility = data.get('volatility', 0)
        
        # More sensitive scalping triggers for auto-trading
        if abs(change_1h) > 0.2 or volatility > 0.5:
            if change_1h < -0.1:  # Recent dip - LONG opportunity
                return {
                    "action": "TRADE",
                    "pair": pair,
                    "direction": "LONG",
                    "entry_price": price,
                    "stop_loss": round(price * (1 - self.scalp_stop_loss), 4),
                    "take_profit": round(price * (1 + self.scalp_take_profit), 4),
                    "position_size_usd": self.trade_size_usd,
                    "confidence": 65,
                    "timeframe": "10-20min",
                    "reason": f"Quick bounce scalping: {pair} dipped {change_1h:.2f}%",
                    "urgency": "high"
                }
            elif change_1h > 0.1:  # Recent pump - SHORT opportunity
                return {
                    "action": "TRADE",
                    "pair": pair,
                    "direction": "SHORT", 
                    "entry_price": price,
                    "stop_loss": round(price * (1 + self.scalp_stop_loss), 4),
                    "take_profit": round(price * (1 - self.scalp_take_profit), 4),
                    "position_size_usd": self.trade_size_usd,
                    "confidence": 65,
                    "timeframe": "10-20min",
                    "reason": f"Pullback scalping: {pair} rose {change_1h:.2f}%, expecting retracement",
                    "urgency": "high"
                }
        
        # Random scalping in high volatility - both directions
        import random
        if volatility > 0.8 and random.random() > 0.6:
            direction = "LONG" if random.random() > 0.5 else "SHORT"
            reason = f"Volatility scalping: {pair} has {volatility:.2f}% volatility"
            
            if direction == "LONG":
                return {
                    "action": "TRADE",
                    "pair": pair,
                    "direction": direction,
                    "entry_price": price,
                    "stop_loss": round(price * (1 - self.scalp_stop_loss), 4),
                    "take_profit": round(price * (1 + self.scalp_take_profit), 4),
                    "position_size_usd": self.trade_size_usd,
                    "confidence": 60,
                    "timeframe": "5-15min",
                    "reason": reason,
                    "urgency": "medium"
                }
            else:
                return {
                    "action": "TRADE",
                    "pair": pair,
                    "direction": direction,
                    "entry_price": price,
                    "stop_loss": round(price * (1 + self.scalp_stop_loss), 4),
                    "take_profit": round(price * (1 - self.scalp_take_profit), 4),
                    "position_size_usd": self.trade_size_usd,
                    "confidence": 60,
                    "timeframe": "5-15min",
                    "reason": reason,
                    "urgency": "medium"
                }
        
        return {
            "action": "SKIP", 
            "confidence": 40,
            "reason": f"Low volatility/opportunity for scalping"
        }

    def execute_scalping_trade(self, decision):
        """COMPLETELY FIXED version with proper TP/SL validation"""
        try:
            pair = decision["pair"]
            direction = decision["direction"]
            
            print(f"🎯 TRADE DIRECTION: {direction}")
            
            # Check if we can open new trade
            if len(self.active_trades) >= self.max_concurrent_trades:
                print(f"⚠️ Maximum trades reached ({self.max_concurrent_trades}), skipping {pair}")
                return
            
            # Check if this pair already has active trade
            if pair in self.active_trades:
                print(f"⚠️ Already have active trade for {pair}, skipping")
                return
            
            # Get REAL current price - with validation
            ticker = self.binance.futures_symbol_ticker(symbol=pair)
            current_price = float(ticker['price'])
            print(f"🔍 Current {pair} price: ${current_price}")
            
            # Validate price is reasonable
            if current_price <= 0.1:
                print(f"❌ Invalid price for {pair}: ${current_price}, skipping trade")
                return
            
            # Calculate quantity with proper precision
            quantity = self.get_quantity(pair, current_price)
            
            print(f"⚡ EXECUTING {direction}: {quantity} {pair} @ ${current_price}")
            
            # Use current price as safe entry price (fallback)
            safe_entry_price = current_price
            
            # MARKET ENTRY
            try:
                if direction == "LONG":
                    order = self.binance.futures_create_order(
                        symbol=pair,
                        side='BUY',
                        type='MARKET',
                        quantity=quantity
                    )
                    # Try to get actual entry price, fallback to safe price
                    actual_entry = float(order.get('avgPrice', 0))
                    if actual_entry <= 0.1:
                        actual_entry = safe_entry_price
                    print(f"✅ LONG ENTRY: ${actual_entry}")
                else:  # SHORT
                    order = self.binance.futures_create_order(
                        symbol=pair,
                        side='SELL',
                        type='MARKET',
                        quantity=quantity
                    )
                    # Try to get actual entry price, fallback to safe price
                    actual_entry = float(order.get('avgPrice', 0))
                    if actual_entry <= 0.1:
                        actual_entry = safe_entry_price
                    print(f"✅ SHORT ENTRY: ${actual_entry}")
            except Exception as order_error:
                print(f"❌ Entry order failed: {order_error}")
                return
            
            # Use the validated entry price
            entry_price = actual_entry
            
            # Calculate TP/SL with PROPER validation
            if direction == "LONG":
                stop_loss = entry_price * (1 - self.scalp_stop_loss)
                take_profit = entry_price * (1 + self.scalp_take_profit)
                print(f"🎯 LONG: Entry=${entry_price}, TP=${take_profit:.4f} (+{self.scalp_take_profit*100}%), SL=${stop_loss:.4f} (-{self.scalp_stop_loss*100}%)")
            else:  # SHORT
                stop_loss = entry_price * (1 + self.scalp_stop_loss)      # SL above entry
                take_profit = entry_price * (1 - self.scalp_take_profit)  # TP below entry
                print(f"🎯 SHORT: Entry=${entry_price}, TP=${take_profit:.4f} (-{self.scalp_take_profit*100}%), SL=${stop_loss:.4f} (+{self.scalp_stop_loss*100}%)")
            
            # Format prices according to symbol precision
            stop_loss = self.format_price(pair, stop_loss)
            take_profit = self.format_price(pair, take_profit)
            
            # CRITICAL: Validate TP/SL are on correct sides of entry
            if direction == "LONG":
                if take_profit <= entry_price:
                    print(f"❌ INVALID LONG TP: TP${take_profit} <= Entry${entry_price}")
                    take_profit = entry_price * (1 + self.scalp_take_profit)  # Recalculate
                    take_profit = self.format_price(pair, take_profit)
                if stop_loss >= entry_price:
                    print(f"❌ INVALID LONG SL: SL${stop_loss} >= Entry${entry_price}")
                    stop_loss = entry_price * (1 - self.scalp_stop_loss)  # Recalculate
                    stop_loss = self.format_price(pair, stop_loss)
            else:  # SHORT
                if take_profit >= entry_price:
                    print(f"❌ INVALID SHORT TP: TP${take_profit} >= Entry${entry_price}")
                    take_profit = entry_price * (1 - self.scalp_take_profit)  # Recalculate
                    take_profit = self.format_price(pair, take_profit)
                if stop_loss <= entry_price:
                    print(f"❌ INVALID SHORT SL: SL${stop_loss} <= Entry${entry_price}")
                    stop_loss = entry_price * (1 + self.scalp_stop_loss)  # Recalculate
                    stop_loss = self.format_price(pair, stop_loss)
            
            # Final validation of prices
            if stop_loss <= 0.01 or take_profit <= 0.01:
                print(f"❌ Invalid TP/SL prices: TP=${take_profit}, SL=${stop_loss}")
                return
            
            print(f"✅ VALIDATED: TP=${take_profit}, SL=${stop_loss}")
            
            # Place TP/SL orders with proper price formatting
            try:
                if direction == "LONG":
                    # STOP LOSS
                    self.binance.futures_create_order(
                        symbol=pair,
                        side='SELL',
                        type='STOP_MARKET',
                        quantity=quantity,
                        stopPrice=stop_loss,
                        timeInForce='GTC',
                        reduceOnly=True
                    )
                    # TAKE PROFIT
                    self.binance.futures_create_order(
                        symbol=pair,
                        side='SELL',
                        type='LIMIT',
                        quantity=quantity,
                        price=take_profit,
                        timeInForce='GTC',
                        reduceOnly=True
                    )
                else:  # SHORT
                    # STOP LOSS
                    self.binance.futures_create_order(
                        symbol=pair,
                        side='BUY',
                        type='STOP_MARKET',
                        quantity=quantity,
                        stopPrice=stop_loss,
                        timeInForce='GTC',
                        reduceOnly=True
                    )
                    # TAKE PROFIT
                    self.binance.futures_create_order(
                        symbol=pair,
                        side='BUY',
                        type='LIMIT',
                        quantity=quantity,
                        price=take_profit,
                        timeInForce='GTC',
                        reduceOnly=True
                    )
            except Exception as sl_tp_error:
                print(f"❌ TP/SL order failed: {sl_tp_error}")
                # Try to close the position if TP/SL fails
                try:
                    if direction == "LONG":
                        self.binance.futures_create_order(
                            symbol=pair,
                            side='SELL',
                            type='MARKET',
                            quantity=quantity,
                            reduceOnly=True
                        )
                    else:
                        self.binance.futures_create_order(
                            symbol=pair,
                            side='BUY',
                            type='MARKET',
                            quantity=quantity,
                            reduceOnly=True
                        )
                    print(f"⚠️ Position closed due to TP/SL error")
                except:
                    print(f"❌ Failed to close position")
                return
            
            # Store trade info
            self.active_trades[pair] = {
                "pair": pair,
                "direction": direction,
                "entry_price": entry_price,
                "quantity": quantity,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "entry_time": time.time(),
                "confidence": decision["confidence"]
            }
            
            print(f"🚀 {direction} TRADE ACTIVATED!")
            print(f"   Active Trades: {list(self.active_trades.keys())}")
            
        except Exception as e:
            print(f"❌ {direction} trade execution failed: {e}")
            import traceback
            traceback.print_exc()

    def check_scalping_trades(self):
        """Check all active trades status"""
        if not self.active_trades:
            return
        
        completed_trades = []
        
        for pair, trade_info in self.active_trades.items():
            try:
                # Check if position still exists
                positions = self.binance.futures_position_information(symbol=pair)
                position = next((p for p in positions if float(p['positionAmt']) != 0), None)
                
                if not position:
                    # Trade completed
                    exit_time = time.time()
                    trade_duration = (exit_time - trade_info["entry_time"]) / 60
                    
                    print(f"💰 TRADE COMPLETED: {pair}!")
                    print(f"   Direction: {trade_info['direction']}")
                    print(f"   Duration: {trade_duration:.1f} minutes")
                    print(f"   Confidence: {trade_info['confidence']}%")
                    
                    completed_trades.append(pair)
                    
            except Exception as e:
                print(f"❌ Trade check error for {pair}: {e}")
        
        # Remove completed trades
        for pair in completed_trades:
            del self.active_trades[pair]
        
        if completed_trades:
            print(f"📊 Remaining Active Trades: {list(self.active_trades.keys())}")

    def run_scalping_cycle(self):
        """Single scalping cycle for multiple pairs"""
        try:
            # Auto rotate pairs if needed
            self.auto_rotate_pairs()
            
            # Get market data for current pairs (excluding already traded pairs)
            market_data = self.get_detailed_market_data()
            
            if not market_data:
                print("⚠️ No market data available, skipping cycle...")
                return
            
            # Display current status
            print(f"\n📊 CURRENT STATUS:")
            print(f"   Available Pairs: {len(self.available_pairs)}")
            print(f"   Active Trades: {len(self.active_trades)}/{self.max_concurrent_trades}")
            if self.active_trades:
                print(f"   Trading Pairs: {list(self.active_trades.keys())}")
            
            # Get AI decision for each available pair
            trade_opportunities = []
            
            for pair in self.available_pairs:
                if pair in self.active_trades:
                    continue  # Skip pairs with active trades
                    
                if pair in market_data:
                    pair_data = {pair: market_data[pair]}
                    decision = self.get_scalping_decision(pair_data)
                    
                    if decision["action"] == "TRADE" and decision["confidence"] >= 65:
                        trade_opportunities.append((decision, decision["confidence"]))
            
            # Sort by confidence and execute top opportunities
            trade_opportunities.sort(key=lambda x: x[1], reverse=True)
            
            for decision, confidence in trade_opportunities:
                if len(self.active_trades) >= self.max_concurrent_trades:
                    break
                    
                urgency = decision.get("urgency", "medium")
                if urgency == "high" or (urgency == "medium" and confidence >= 70):
                    print(f"🎯 EXECUTING SCALPING: {decision['pair']} {decision['direction']}")
                    self.execute_scalping_trade(decision)
                    time.sleep(2)  # Small delay between executions
            
            # Check all active trades
            self.check_scalping_trades()
            
        except Exception as e:
            print(f"❌ Scalping cycle error: {e}")

    def start_auto_trading(self):
        """Main auto trading loop"""
        print("🚀 STARTING MULTI-PAIR SCALPING BOT (NO BTC)!")
        
        # Initial pair selection
        self.available_pairs = self.get_ai_recommended_pairs()
        self.last_rotation_time = time.time()
        
        cycle_count = 0
        
        while True:
            try:
                cycle_count += 1
                print(f"\n{'='*60}")
                print(f"🔄 CYCLE {cycle_count} - {time.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"{'='*60}")
                
                # Run scalping cycle
                self.run_scalping_cycle()
                
                # Status update every 10 cycles
                if cycle_count % 10 == 0:
                    print(f"\n📈 BOT STATUS UPDATE:")
                    print(f"   Total Cycles: {cycle_count}")
                    print(f"   Available Pairs: {len(self.available_pairs)}")
                    print(f"   Active Trades: {len(self.active_trades)}/{self.max_concurrent_trades}")
                    print(f"   Next Rotation: {time.strftime('%H:%M:%S', time.localtime(self.last_rotation_time + self.pair_rotation_hours * 3600))}")
                
                time.sleep(60)  # 1 minute between cycles
                
            except KeyboardInterrupt:
                print(f"\n🛑 BOT STOPPED BY USER")
                if self.active_trades:
                    print(f"   Active Trades: {list(self.active_trades.keys())}")
                break
            except Exception as e:
                print(f"❌ Main loop error: {e}")
                time.sleep(30)

# 🚀 START MULTI-PAIR SCALPING BOT
if __name__ == "__main__":
    try:
        bot = MultiPairScalpingTrader()
        bot.start_auto_trading()
    except Exception as e:
        print(f"❌ Failed to start bot: {e}")
