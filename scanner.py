import requests
import pandas as pd
import math

BINANCE_API_URL = "https://api.binance.com/api/v3"

def get_top_coins(limit=50):
    try:
        url = f"{BINANCE_API_URL}/ticker/24hr"
        response = requests.get(url)
        data = response.json()
        
        # Filter USDT pairs and sort by quoteVolume
        usdt_pairs = [d for d in data if d['symbol'].endswith('USDT')]
        usdt_pairs.sort(key=lambda x: float(x['quoteVolume']), reverse=True)
        
        top_symbols = [pair['symbol'] for pair in usdt_pairs[:limit]]
        return top_symbols
    except Exception as e:
        print(f"Error fetching top coins: {e}")
        return []

def get_klines(symbol, interval, limit=100):
    try:
        url = f"{BINANCE_API_URL}/klines"
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        response = requests.get(url, params=params)
        data = response.json()
        
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        
        return df
    except Exception as e:
        print(f"Error fetching klines for {symbol}: {e}")
        return pd.DataFrame()

def detect_patterns(df):
    if df.empty or len(df) < 5:
        return None
        
    # Basic logic for demonstration. In a real app, you'd use more robust peak/trough detection.
    # Looking at the last 5 periods to find simple formations.
    closes = df['close'].values
    highs = df['high'].values
    lows = df['low'].values
    
    # Very naive Double Top detection:
    # Requires two peaks of similar height separated by a dip.
    # Let's say last 20 candles for context.
    if len(df) >= 20:
        recent_highs = highs[-20:]
        max1 = max(recent_highs[:10])
        max2 = max(recent_highs[10:])
        if abs(max1 - max2) / max1 < 0.005:  # Within 0.5%
            return "Çift Tepe (Double Top)", "Düşüş"
            
    # Very naive Double Bottom detection:
    if len(df) >= 20:
        recent_lows = lows[-20:]
        min1 = min(recent_lows[:10])
        min2 = min(recent_lows[10:])
        if abs(min1 - min2) / min1 < 0.005:  # Within 0.5%
            return "Çift Dip (Double Bottom)", "Yükseliş"

    # Head and Shoulders (OBO)
    if len(df) >= 30:
        # Simplistic approach
        pass

    return None

def scan_markets(limit=50, interval='1h'):
    symbols = get_top_coins(limit)
    results = []
    
    for symbol in symbols:
        df = get_klines(symbol, interval, limit=50)
        pattern = detect_patterns(df)
        if pattern:
            formation, direction = pattern
            results.append({
                "coin": symbol.replace('USDT', ''),
                "exchange": "Binance",
                "timeframe": interval,
                "formation": formation,
                "direction": direction,
                "chart_link": f"https://www.tradingview.com/chart/?symbol=BINANCE:{symbol}"
            })
            
    return results
