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

class MultiPositionFutureTrader:
    def __init__(self):
        # Load config from .env file
        self.binance_api_key = os.getenv('BINANCE_API_KEY')
        self.binance_secret = os.getenv('BINANCE_SECRET_KEY')
        self.deepseek_key = os.getenv('DEEPSEEK_API_KEY')
        
        # Trading parameters from .env
        self.trade_size_usd = int(os.getenv('TRADE_SIZE', 200))
        self.leverage = int(os.getenv('LEVERAGE', 10))
        self.risk_percentage = float(os.getenv('RISK_PERCENTAGE', 1.0))
        self.max_positions = int(os.getenv('MAX_POSITIONS', 3))  # Maximum concurrent positions
        
        # Initialize Binance client
        self.binance = Client(self.binance_api_key, self.binance_secret)
        
        self.available_pairs = ["ETHUSDT", "SOLUSDT", "ADAUSDT", "BNB"]
        self.active_trades = {}  # Dictionary to store multiple active trades
        self.max_trades_per_pair = 1  # Only one trade per pair at a time
        
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
        print(f"   Max Positions: {self.max_positions}")
        print(f"   Available Pairs: {', '.join(self.available_pairs)}")
    
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
    
    def run_multi_position_trading(self):
        """Main trading loop for multiple positions"""
        print("🚀 MULTI-POSITION FUTURES BOT STARTED!")
        print("⚙️  Configuration: .env file")
        print(f"💵 Trade Size: ${self.trade_size_usd}")
        print(f"📈 Leverage: {self.leverage}x")
        print(f"🎯 Risk: {self.risk_percentage}%")
        print(f"📊 Max Positions: {self.max_positions}")
        
        while True:
            try:
                # 1. Get market data for all pairs
                market_data = self.get_detailed_market_data()
                
                # 2. Get AI decisions for all pairs
                decisions = self.get_multi_pair_decisions(market_data)
                
                # 3. Execute trades for each pair
                self.execute_multi_trades(decisions, market_data)
                
                # 4. Check and manage all active trades
                self.check_all_active_trades()
                
                # 5. Display portfolio status
                self.display_portfolio_status()
                
                time.sleep(300)  # 5 minutes
                
            except Exception as e:
                print(f"❌ Error: {e}")
                time.sleep(60)
    
    def get_multi_pair_decisions(self, market_data):
        """Get trading decisions for multiple pairs"""
        decisions = {}
        
        for pair in self.available_pairs:
            # Skip if we already have an active trade for this pair
            if pair in self.active_trades:
                decisions[pair] = {"action": "SKIP", "reason": f"Active trade exists for {pair}"}
                continue
            
            # Get individual decision for each pair
            pair_market_data = {pair: market_data[pair]}
            decision = self.get_deepseek_autonomous_decision(pair_market_data)
            decisions[pair] = decision
        
        return decisions
    
    def execute_multi_trades(self, decisions, market_data):
        """Execute trades for multiple pairs based on decisions"""
        current_positions = len(self.active_trades)
        available_slots = self.max_positions - current_positions
        
        print(f"📊 Trading Status: {current_positions}/{self.max_positions} positions active")
        
        if available_slots <= 0:
            print("⏸️ Maximum positions reached, waiting for slots...")
            return
        
        executed_trades = 0
        
        for pair, decision in decisions.items():
            if executed_trades >= available_slots:
                break
                
            if decision["action"] == "TRADE" and decision["confidence"] >= 70:
                if pair not in self.active_trades:
                    print(f"🎯 EXECUTING: {decision['pair']} {decision['direction']}")
                    success = self.execute_autonomous_trade(decision)
                    if success:
                        executed_trades += 1
                        print(f"✅ Trade executed for {pair} ({executed_trades}/{available_slots} slots used)")
    
    def execute_autonomous_trade(self, decision):
        """Execute trade for a single pair - returns True if successful"""
        try:
            pair = decision["pair"]
            direction = decision["direction"]
            suggested_price = decision["entry_price"]
            stop_loss = decision["stop_loss"]
            take_profit = decision["take_profit"]
            
            # Get current market price for accurate quantity calculation
            ticker = self.binance.futures_symbol_ticker(symbol=pair)
            current_market_price = float(ticker['price'])
            
            print(f"🔧 Setting up trade for {pair}:")
            print(f"   Direction: {direction}")
            print(f"   Trade Size: ${self.trade_size_usd}")
            print(f"   Market Price: ${current_market_price}")
            
            # Get safe quantity with proper precision
            quantity = self.get_safe_quantity(pair, current_market_price)
            
            if not quantity or quantity <= 0:
                print(f"❌ Invalid quantity calculation for {pair}")
                return False
            
            # 1. MARKET ENTRY - Immediate execution
            print(f"📥 Placing MARKET entry order for {pair}...")
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
            
            # Wait for position to open
            time.sleep(2)
            
            # 2. STOP LOSS
            print(f"🛡️ Placing STOP LOSS for {pair}...")
            if direction == "LONG":
                sl_order = self.binance.futures_create_order(
                    symbol=pair,
                    side='SELL',
                    type='STOP_MARKET',
                    quantity=quantity,
                    stopPrice=str(round(stop_loss, 2)),
                    timeInForce='GTC',
                    reduceOnly=True
                )
            else:  # SHORT
                sl_order = self.binance.futures_create_order(
                    symbol=pair,
                    side='BUY',
                    type='STOP_MARKET',
                    quantity=quantity,
                    stopPrice=str(round(stop_loss, 2)),
                    timeInForce='GTC',
                    reduceOnly=True
                )
            
            # 3. TAKE PROFIT
            print(f"🎯 Placing TAKE PROFIT for {pair}...")
            if direction == "LONG":
                tp_order = self.binance.futures_create_order(
                    symbol=pair,
                    side='SELL',
                    type='LIMIT',
                    quantity=quantity,
                    price=str(round(take_profit, 2)),
                    timeInForce='GTC',
                    reduceOnly=True
                )
            else:  # SHORT
                tp_order = self.binance.futures_create_order(
                    symbol=pair,
                    side='BUY',
                    type='LIMIT',
                    quantity=quantity,
                    price=str(round(take_profit, 2)),
                    timeInForce='GTC',
                    reduceOnly=True
                )
            
            # Save trade info
            self.active_trades[pair] = {
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
                "status": "ACTIVE",
                "reason": decision["reason"]
            }
            
            print(f"🎉 TRADE EXECUTED SUCCESSFULLY for {pair}!")
            print(f"   Entry: ${actual_entry_price}")
            print(f"   Stop Loss: ${stop_loss}")
            print(f"   Take Profit: ${take_profit}")
            
            return True
            
        except Exception as e:
            print(f"❌ Trade execution failed for {pair}: {e}")
            # Try to emergency close if position was opened
            try:
                if 'entry_order' in locals():
                    self.emergency_close_position(pair, direction, quantity)
            except:
                pass
            return False

    def check_all_active_trades(self):
        """Check and manage all active trades"""
        pairs_to_remove = []
        
        for pair, trade_info in self.active_trades.items():
            try:
                # Check if position still exists
                positions = self.binance.futures_position_information(symbol=pair)
                position = next((p for p in positions if float(p['positionAmt']) != 0), None)
                
                if not position:
                    print(f"💰 POSITION CLOSED for {pair}! Removing from active trades.")
                    pairs_to_remove.append(pair)
                    continue
                
                # Check TP/SL orders status
                try:
                    tp_order = self.binance.futures_get_order(
                        symbol=pair,
                        orderId=trade_info["tp_order_id"]
                    )
                    sl_order = self.binance.futures_get_order(
                        symbol=pair,
                        orderId=trade_info["sl_order_id"]
                    )
                    
                    if tp_order['status'] == 'FILLED':
                        print(f"🎯 TAKE PROFIT HIT for {pair}! Trade completed.")
                        pairs_to_remove.append(pair)
                    elif sl_order['status'] == 'FILLED':
                        print(f"🛡️ STOP LOSS HIT for {pair}! Trade closed.")
                        pairs_to_remove.append(pair)
                        
                except Exception as e:
                    # Orders might be cancelled or modified
                    pass
                    
            except Exception as e:
                print(f"❌ Error checking trade for {pair}: {e}")
        
        # Remove completed trades
        for pair in pairs_to_remove:
            if pair in self.active_trades:
                del self.active_trades[pair]
    
    def display_portfolio_status(self):
        """Display current portfolio status"""
        if not self.active_trades:
            print("📊 Portfolio: No active positions")
            return
        
        print(f"📊 PORTFOLIO STATUS: {len(self.active_trades)} active positions")
        print("-" * 50)
        
        total_invested = 0
        total_unrealized_pnl = 0
        
        for pair, trade in self.active_trades.items():
            try:
                positions = self.binance.futures_position_information(symbol=pair)
                position = next((p for p in positions if float(p['positionAmt']) != 0), None)
                
                if position:
                    unrealized_pnl = float(position['unRealizedProfit'])
                    current_price = float(position['markPrice'])
                    
                    total_invested += trade['size_usd']
                    total_unrealized_pnl += unrealized_pnl
                    
                    pnl_percent = (unrealized_pnl / trade['size_usd']) * 100
                    pnl_emoji = "🟢" if unrealized_pnl > 0 else "🔴" if unrealized_pnl < 0 else "⚪"
                    
                    print(f"{pnl_emoji} {pair} {trade['direction']}: "
                          f"Entry ${trade['entry_price']} | "
                          f"Current ${current_price} | "
                          f"P&L ${unrealized_pnl:+.2f} ({pnl_percent:+.1f}%)")
            
            except Exception as e:
                print(f"❌ Error getting position info for {pair}: {e}")
        
        if total_invested > 0:
            total_pnl_percent = (total_unrealized_pnl / total_invested) * 100
            total_emoji = "🟢" if total_unrealized_pnl > 0 else "🔴" if total_unrealized_pnl < 0 else "⚪"
            print("-" * 50)
            print(f"{total_emoji} TOTAL: Invested ${total_invested} | "
                  f"P&L ${total_unrealized_pnl:+.2f} ({total_pnl_percent:+.1f}%)")
    
    # Keep all the helper methods from previous code (get_safe_quantity, get_step_precision, etc.)
    # ... [All the helper methods remain the same] ...
    
    def get_safe_quantity(self, pair, entry_price):
        """Safe quantity calculation with proper precision handling"""
        try:
            # Get symbol info from exchange
            symbol_info = self.binance.futures_exchange_info()
            pair_info = next((s for s in symbol_info['symbols'] if s['symbol'] == pair), None)
            
            if pair_info:
                lot_size_filter = next((f for f in pair_info['filters'] if f['filterType'] == 'LOT_SIZE'), None)
                if lot_size_filter:
                    min_qty = float(lot_size_filter['minQty'])
                    max_qty = float(lot_size_filter['maxQty'])
                    step_size = float(lot_size_filter['stepSize'])
                    
                    # Calculate ideal quantity
                    raw_quantity = self.trade_size_usd / entry_price
                    
                    # Ensure minimum quantity
                    quantity = max(raw_quantity, min_qty)
                    
                    # Ensure maximum quantity
                    quantity = min(quantity, max_qty)
                    
                    # Round to step size
                    precision = self.get_step_precision(step_size)
                    quantity = (quantity // step_size) * step_size
                    quantity = round(quantity, precision)
                    
                    # Final validation
                    notional_value = entry_price * quantity
                    if notional_value < 10:  # Binance minimum notional
                        print(f"⚠️ Notional too low for {pair}: ${notional_value:.2f}")
                        return None
                    
                    return quantity
                    
        except Exception as e:
            print(f"⚠️ Precision error for {pair}: {e}")
        
        # Fallback to manual precision
        return self.apply_pair_precision(pair, self.trade_size_usd / entry_price)

    def get_step_precision(self, step_size):
        """Calculate precision from step size"""
        if step_size >= 1:
            return 0  # Whole numbers
        else:
            step_str = format(step_size, '.10f').rstrip('0').rstrip('.')
            if '.' in step_str:
                return len(step_str.split('.')[1])
            else:
                return 0

    def apply_pair_precision(self, pair, quantity):
        """Apply pair-specific quantity precision"""
        precision_map = {
            "BTCUSDT": 3,   # 0.001 BTC
            "ETHUSDT": 3,   # 0.001 ETH
            "SOLUSDT": 1,   # 0.1 SOL
            "ADAUSDT": 0,   # 1 ADA (whole numbers only)
        }
        
        min_quantities = {
            "BTCUSDT": 0.001,
            "ETHUSDT": 0.001,
            "SOLUSDT": 0.1,
            "ADAUSDT": 1.0,
        }
        
        precision = precision_map.get(pair, 3)
        min_qty = min_quantities.get(pair, 0.001)
        
        quantity = max(quantity, min_qty)
        
        if precision == 0:
            quantity = int(quantity)
        else:
            quantity = round(quantity, precision)
        
        return quantity

    def emergency_close_position(self, pair, direction, quantity):
        """Emergency close position"""
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
            print(f"🚨 EMERGENCY POSITION CLOSED for {pair}")
        except Exception as e:
            print(f"❌ Emergency close failed for {pair}: {e}")

    def get_detailed_market_data(self):
        """Get comprehensive market data"""
        market_data = {}
        
        for pair in self.available_pairs:
            try:
                ticker = self.binance.futures_symbol_ticker(symbol=pair)
                price = float(ticker['price'])
                
                klines = self.binance.futures_klines(
                    symbol=pair,
                    interval=Client.KLINE_INTERVAL_15MINUTE,
                    limit=20
                )
                
                closes = [float(k[4]) for k in klines]
                highs = [float(k[2]) for k in klines]
                lows = [float(k[3]) for k in klines]
                volumes = [float(k[5]) for k in klines]
                
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

    def get_deepseek_autonomous_decision(self, market_data):
        """DeepSeek AI decision for individual pair"""
        pair = list(market_data.keys())[0]  # Get the single pair
        
        prompt = f"""
        AUTONOMOUS TRADING ANALYSIS FOR {pair}:
        
        CONFIGURATION:
        - Trade Size: ${self.trade_size_usd}
        - Leverage: {self.leverage}x
        - Risk: {self.risk_percentage}%
        
        MARKET DATA: {json.dumps(market_data, indent=2)}
        
        Analyze ONLY {pair} and provide trading decision.
        
        RESPONSE (JSON):
        {{
            "action": "TRADE/SKIP",
            "pair": "{pair}",
            "direction": "LONG/SHORT",
            "entry_price": number,
            "stop_loss": number,
            "take_profit": number,
            "position_size_usd": {self.trade_size_usd},
            "confidence": 0-100,
            "reason": "Technical analysis for {pair}..."
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
            "max_tokens": 800
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
            
            return self.get_fallback_decision(market_data)
                
        except Exception as e:
            print(f"❌ API error for {pair}: {e}")
            return self.get_fallback_decision(market_data)

    def get_fallback_decision(self, market_data):
        """Fallback decision when API fails"""
        pair = list(market_data.keys())[0]
        data = market_data[pair]
        price = data['price']
        change = data.get('change_24h', 0)
        volume_ratio = data.get('volume_ratio', 1)
        
        if abs(change) > 1.5 and volume_ratio > 1.1:
            if change < -1.5:
                return {
                    "action": "TRADE",
                    "pair": pair,
                    "direction": "LONG",
                    "entry_price": price,
                    "stop_loss": round(price * 0.99, 2),
                    "take_profit": round(price * 1.015, 2),
                    "position_size_usd": self.trade_size_usd,
                    "confidence": 70,
                    "reason": f"Fallback: {pair} oversold bounce setup"
                }
            else:
                return {
                    "action": "TRADE",
                    "pair": pair,
                    "direction": "SHORT",
                    "entry_price": price,
                    "stop_loss": round(price * 1.01, 2),
                    "take_profit": round(price * 0.985, 2),
                    "position_size_usd": self.trade_size_usd,
                    "confidence": 70,
                    "reason": f"Fallback: {pair} overbought pullback setup"
                }
        
        return {
            "action": "SKIP",
            "confidence": 50,
            "reason": f"Fallback: No clear signals for {pair}"
        }

# 🚀 START MULTI-POSITION BOT
if __name__ == "__main__":
    try:
        bot = MultiPositionFutureTrader()
        bot.run_multi_position_trading()
    except Exception as e:
        print(f"❌ Failed to start bot: {e}")
