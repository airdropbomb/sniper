import ccxt
import talib
import pandas as pd
import numpy as np
import time
import os
from datetime import datetime
from dotenv import load_dotenv
import logging

# Setup logging
logging.basicConfig(
    filename='sniper_bot.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Load .env file
load_dotenv()

# Binance Demo Trading configuration
exchange = ccxt.binance({
    'apiKey': os.getenv('BINANCE_API_KEY'),
    'secret': os.getenv('BINANCE_SECRET'),
    'enableDemoTrading': True,  # Demo trading mode
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future',  # Futures market
    },
})

# Trading parameters
symbol = 'BTC/USDT'
timeframe = '1m'
leverage = 5
amount_usdt = 100  # Position size in USDT (small for testing)
max_position_size = 0.05  # Max 5% of account balance

# Mock news sentiment function (replace with real NewsAPI or NLP model)
def get_news_sentiment():
    """Mock sentiment score (-1 to 1)"""
    # Real implementation: Use NewsAPI or scrape Twitter/X for sentiment
    sentiment = np.random.uniform(-1, 1)
    logging.info(f"Generated mock sentiment: {sentiment:.2f}")
    return sentiment

# Fetch OHLCV data
def fetch_ohlcv(symbol, timeframe, limit=100):
    """Fetch OHLCV data"""
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        logging.info("Successfully fetched OHLCV data")
        return df
    except Exception as e:
        logging.error(f"Error fetching OHLCV: {e}")
        return None

# Calculate indicators
def calculate_indicators(df):
    """Calculate RSI, EMA, and ATR"""
    try:
        close = df['close'].values
        rsi = talib.RSI(close, timeperiod=14)
        ema_fast = talib.EMA(close, timeperiod=9)
        ema_slow = talib.EMA(close, timeperiod=21)
        atr = talib.ATR(df['high'].values, df['low'].values, close, timeperiod=14)
        indicators = {
            'rsi': rsi[-1] if not np.isnan(rsi[-1]) else 50,
            'ema_crossover': ema_fast[-1] > ema_slow[-1] if not np.isnan(ema_fast[-1]) else False,
            'ema_crossunder': ema_fast[-1] < ema_slow[-1] if not np.isnan(ema_fast[-1]) else False,
            'atr': atr[-1] if not np.isnan(atr[-1]) else 0
        }
        logging.info(f"Indicators: RSI={indicators['rsi']:.2f}, ATR={indicators['atr']:.2f}")
        return indicators
    except Exception as e:
        logging.error(f"Error calculating indicators: {e}")
        return {'rsi': 50, 'ema_crossover': False, 'ema_crossunder': False, 'atr': 0}

# Dynamic SL/TP based on volatility and sentiment
def calculate_sl_tp(entry_price, atr, sentiment):
    """Calculate dynamic stop-loss and take-profit"""
    try:
        volatility_factor = atr / entry_price
        base_sl = 0.02  # 2% base stop-loss
        base_tp = 0.04  # 4% base take-profit
        sl_pct = base_sl * (1 + abs(sentiment) * 0.5) * (1 + volatility_factor)
        tp_pct = base_tp * (1 + abs(sentiment) * 0.5) * (1 + volatility_factor)
        logging.info(f"SL: {sl_pct*100:.2f}%, TP: {tp_pct*100:.2f}%")
        return sl_pct, tp_pct
    except Exception as e:
        logging.error(f"Error calculating SL/TP: {e}")
        return 0.02, 0.04

# Get current position
def get_position():
    """Check current position"""
    try:
        positions = exchange.fetch_positions([symbol])
        for pos in positions:
            if pos['symbol'] == symbol and float(pos['contracts']) != 0:
                logging.info(f"Position: {pos['side']} {pos['contracts']} at avg {pos['entryPrice']}")
                return pos
        return None
    except Exception as e:
        logging.error(f"Error fetching position: {e}")
        return None

# Open long position
def open_long_position(amount_usdt, sl_pct, tp_pct):
    """Open long position with SL/TP"""
    try:
        ticker = exchange.fetch_ticker(symbol)
        price = ticker['last']
        amount = amount_usdt / price
        order = exchange.create_market_buy_order(symbol, amount)
        sl_price = price * (1 - sl_pct)
        tp_price = price * (1 + tp_pct)
        exchange.create_stop_limit_order(symbol, 'sell', amount, sl_price, None, {'stopPrice': sl_price})
        exchange.create_limit_sell_order(symbol, amount, tp_price)
        logging.info(f"Long opened: {amount} {symbol} at {price}, SL: {sl_price}, TP: {tp_price}")
        return order
    except Exception as e:
        logging.error(f"Error opening long position: {e}")
        return None

# Open short position
def open_short_position(amount_usdt, sl_pct, tp_pct):
    """Open short position with SL/TP"""
    try:
        ticker = exchange.fetch_ticker(symbol)
        price = ticker['last']
        amount = amount_usdt / price
        order = exchange.create_market_sell_order(symbol, amount)
        sl_price = price * (1 + sl_pct)
        tp_price = price * (1 - tp_pct)
        exchange.create_stop_limit_order(symbol, 'buy', amount, sl_price, None, {'stopPrice': sl_price})
        exchange.create_limit_buy_order(symbol, amount, tp_price)
        logging.info(f"Short opened: {amount} {symbol} at {price}, SL: {sl_price}, TP: {tp_price}")
        return order
    except Exception as e:
        logging.error(f"Error opening short position: {e}")
        return None

# AI decision logic
def ai_decision(df, sentiment):
    """AI decision based on indicators and sentiment"""
    if df is None:
        logging.warning("No OHLCV data, skipping decision")
        return None, None, None
    indicators = calculate_indicators(df)
    rsi, ema_crossover, ema_crossunder, atr = indicators['rsi'], indicators['ema_crossover'], indicators['ema_crossunder'], indicators['atr']
    
    # Simple decision rules (replace with RL model in production)
    score = 0
    if rsi < 30: score += 0.4  # Oversold
    if rsi > 70: score -= 0.4  # Overbought
    if ema_crossover: score += 0.3  # Bullish trend
    if ema_crossunder: score -= 0.3  # Bearish trend
    score += sentiment * 0.3  # Sentiment impact
    logging.info(f"Decision score: {score:.2f}")
    
    # Calculate dynamic SL/TP
    sl_pct, tp_pct = calculate_sl_tp(df['close'].iloc[-1], atr, sentiment)
    
    # Decision
    if score > 0.5 and get_position() is None:
        return 'long', sl_pct, tp_pct
    elif score < -0.5 and get_position() is None:
        return 'short', sl_pct, tp_pct
    return None, None, None

# Set leverage (with error handling)
try:
    exchange.set_leverage(leverage, symbol)
    logging.info(f"Leverage set to {leverage}x for {symbol}")
except ccxt.NotSupported:
    logging.warning("Leverage setting not supported in demo mode, ensure leverage is set in Binance Demo UI")
except ccxt.AuthenticationError as e:
    logging.error(f"Authentication error setting leverage: {e}")
    print(f"Fatal error: Invalid API key. Please check .env file. Exiting...")
    exit(1)
except Exception as e:
    logging.error(f"Error setting leverage: {e}")

# Main loop
print("AI Sniper Bot started... Press Ctrl+C to stop.")
logging.info("AI Sniper Bot started")
while True:
    try:
        df = fetch_ohlcv(symbol, timeframe)
        sentiment = get_news_sentiment()
        decision, sl_pct, tp_pct = ai_decision(df, sentiment)
        
        if decision == 'long':
            open_long_position(amount_usdt, sl_pct, tp_pct)
        elif decision == 'short':
            open_short_position(amount_usdt, sl_pct, tp_pct)
        else:
            position = get_position()
            if position:
                print(f"Position open: {position['side']} {position['contracts']} at avg {position['entryPrice']}, PnL: {position['unrealizedPnl']}")
            else:
                print(f"No signal. RSI: {calculate_indicators(df)['rsi']:.2f}, Sentiment: {sentiment:.2f}")
        
        time.sleep(60)  # Check every 1 minute
    except KeyboardInterrupt:
        print("Bot stopped by user.")
        logging.info("Bot stopped by user")
        break
    except ccxt.AuthenticationError as e:
        print(f"Fatal error: Invalid API key. Please check .env file. Exiting...")
        logging.error(f"Authentication error: {e}")
        break
    except Exception as e:
        print(f"Error in main loop: {e}")
        logging.error(f"Error in main loop: {e}")
        time.sleep(60)
