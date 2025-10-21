import ccxt
import talib
import pandas as pd
import numpy as np
import time
from datetime import datetime

# Binance API credentials (Testnet အတွက် sandbox=True)
exchange = ccxt.binance({
    'apiKey': 'YOUR_API_KEY_HERE',  # သင့် API key
    'secret': 'YOUR_SECRET_HERE',   # သင့် secret
    'sandbox': True,                # Testnet mode (live ဆို False)
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future',    # Futures market
    },
})

# Trading parameters
symbol = 'BTC/USDT'
timeframe = '1m'
leverage = 5
amount_usdt = 100  # Position size in USDT (small စမ်းပါ)

# Mock news sentiment function (replace with real NewsAPI or NLP model)
def get_news_sentiment():
    """Mock sentiment score (-1 to 1)"""
    # Real implementation: Use NewsAPI or scrape Twitter/X for sentiment
    return np.random.uniform(-1, 1)  # Random sentiment for demo

# Fetch OHLCV data
def fetch_ohlcv(symbol, timeframe, limit=100):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

# Calculate indicators
def calculate_indicators(df):
    close = df['close'].values
    rsi = talib.RSI(close, timeperiod=14)
    ema_fast = talib.EMA(close, timeperiod=9)
    ema_slow = talib.EMA(close, timeperiod=21)
    atr = talib.ATR(df['high'].values, df['low'].values, close, timeperiod=14)
    return {
        'rsi': rsi[-1] if not np.isnan(rsi[-1]) else 50,
        'ema_crossover': ema_fast[-1] > ema_slow[-1] if not np.isnan(ema_fast[-1]) else False,
        'ema_crossunder': ema_fast[-1] < ema_slow[-1] if not np.isnan(ema_fast[-1]) else False,
        'atr': atr[-1] if not np.isnan(atr[-1]) else 0
    }

# Dynamic SL/TP based on volatility and sentiment
def calculate_sl_tp(entry_price, atr, sentiment):
    volatility_factor = atr / entry_price
    base_sl = 0.02  # 2% base stop-loss
    base_tp = 0.04  # 4% base take-profit
    # Adjust SL/TP based on sentiment and volatility
    sl_pct = base_sl * (1 + abs(sentiment) * 0.5) * (1 + volatility_factor)
    tp_pct = base_tp * (1 + abs(sentiment) * 0.5) * (1 + volatility_factor)
    return sl_pct, tp_pct

# Get current position
def get_position():
    positions = exchange.fetch_positions([symbol])
    for pos in positions:
        if pos['symbol'] == symbol and float(pos['contracts']) != 0:
            return pos
    return None

# Open long position
def open_long_position(amount_usdt, sl_pct, tp_pct):
    ticker = exchange.fetch_ticker(symbol)
    price = ticker['last']
    amount = amount_usdt / price
    order = exchange.create_market_buy_order(symbol, amount)
    sl_price = price * (1 - sl_pct)
    tp_price = price * (1 + tp_pct)
    exchange.create_stop_limit_order(symbol, 'sell', amount, sl_price, None, {'stopPrice': sl_price})
    exchange.create_limit_sell_order(symbol, amount, tp_price)
    print(f"Long opened: {amount} {symbol} at {price}, SL: {sl_price}, TP: {tp_price}")
    return order

# Open short position
def open_short_position(amount_usdt, sl_pct, tp_pct):
    ticker = exchange.fetch_ticker(symbol)
    price = ticker['last']
    amount = amount_usdt / price
    order = exchange.create_market_sell_order(symbol, amount)
    sl_price = price * (1 + sl_pct)
    tp_price = price * (1 - tp_pct)
    exchange.create_stop_limit_order(symbol, 'buy', amount, sl_price, None, {'stopPrice': sl_price})
    exchange.create_limit_buy_order(symbol, amount, tp_price)
    print(f"Short opened: {amount} {symbol} at {price}, SL: {sl_price}, TP: {tp_price}")
    return order

# Main AI decision logic
def ai_decision(df, sentiment):
    indicators = calculate_indicators(df)
    rsi, ema_crossover, ema_crossunder, atr = indicators['rsi'], indicators['ema_crossover'], indicators['ema_crossunder'], indicators['atr']
    
    # Simple decision rules (replace with RL model in production)
    score = 0
    if rsi < 30: score += 0.4  # Oversold
    if rsi > 70: score -= 0.4  # Overbought
    if ema_crossover: score += 0.3  # Bullish trend
    if ema_crossunder: score -= 0.3  # Bearish trend
    score += sentiment * 0.3  # Sentiment impact
    
    # Calculate dynamic SL/TP
    sl_pct, tp_pct = calculate_sl_tp(df['close'].iloc[-1], atr, sentiment)
    
    # Decision
    if score > 0.5 and get_position() is None:
        return 'long', sl_pct, tp_pct
    elif score < -0.5 and get_position() is None:
        return 'short', sl_pct, tp_pct
    return None, None, None

# Set leverage
exchange.set_leverage(leverage, symbol)

# Main loop
print("AI Sniper Bot started... Press Ctrl+C to stop.")
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
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(60)
