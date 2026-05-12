import requests
import pandas as pd
import pandas_ta as ta
import numpy as np
from scipy.signal import argrelextrema

BINANCE_API_URL = "https://api.binance.com/api/v3"

def get_top_coins(limit=50):
    try:
        url = f"{BINANCE_API_URL}/ticker/24hr"
        response = requests.get(url)
        data = response.json()
        usdt_pairs = [d for d in data if d['symbol'].endswith('USDT')]
        usdt_pairs.sort(key=lambda x: float(x['quoteVolume']), reverse=True)
        return [pair['symbol'] for pair in usdt_pairs[:limit]]
    except Exception as e:
        print(f"Error fetching top coins: {e}")
        return []

def get_klines(symbol, interval, limit=200):
    try:
        url = f"{BINANCE_API_URL}/klines"
        params = {'symbol': symbol, 'interval': interval, 'limit': limit}
        response = requests.get(url, params=params)
        data = response.json()
        
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'qav', 'num_trades', 'tbbav', 'tbqav', 'ignore'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        return df
    except Exception as e:
        print(f"Error fetching klines: {e}")
        return pd.DataFrame()

def calculate_indicators(df):
    if df.empty or len(df) < 20: return df
    
    # Calculate RSI
    df['RSI'] = ta.rsi(df['close'], length=14)
    
    # Calculate MAs
    df['SMA_20'] = ta.sma(df['close'], length=20)
    df['SMA_50'] = ta.sma(df['close'], length=50)
    df['SMA_200'] = ta.sma(df['close'], length=200)
    
    # Fill NaN
    df.fillna(method='bfill', inplace=True)
    return df

def find_extrema(df, order=5):
    # Find local peaks and troughs
    closes = df['close'].values
    peaks = argrelextrema(closes, np.greater, order=order)[0]
    troughs = argrelextrema(closes, np.less, order=order)[0]
    return peaks, troughs

def find_support_resistance(df, peaks, troughs):
    closes = df['close'].values
    highs = df['high'].values
    lows = df['low'].values
    
    # Very simple S/R based on recent max peaks and min troughs
    if len(peaks) > 0 and len(troughs) > 0:
        resistance = np.max([highs[p] for p in peaks[-3:]]) if len(peaks) >=3 else highs[peaks[-1]]
        support = np.min([lows[t] for t in troughs[-3:]]) if len(troughs) >=3 else lows[troughs[-1]]
        return support, resistance
    return None, None

def detect_advanced_patterns(df, peaks, troughs):
    if len(peaks) < 2 or len(troughs) < 2:
        return None, None
        
    closes = df['close'].values
    
    # Get last 3 peaks and troughs
    recent_peaks = peaks[-3:]
    recent_troughs = troughs[-3:]
    
    # Double Top
    if len(recent_peaks) >= 2:
        p1, p2 = closes[recent_peaks[-2]], closes[recent_peaks[-1]]
        if abs(p1 - p2) / p1 < 0.02: # 2% tolerance
            return "İkili Tepe (Double Top)", "Düşüş"
            
    # Double Bottom
    if len(recent_troughs) >= 2:
        t1, t2 = closes[recent_troughs[-2]], closes[recent_troughs[-1]]
        if abs(t1 - t2) / t1 < 0.02:
            return "İkili Dip (Double Bottom)", "Yükseliş"

    # Head and Shoulders (OBO)
    if len(recent_peaks) >= 3:
        p1, p2, p3 = closes[recent_peaks[-3]], closes[recent_peaks[-2]], closes[recent_peaks[-1]]
        if p2 > p1 and p2 > p3 and abs(p1 - p3) / p1 < 0.03: # Head is highest, shoulders similar
            return "OBO (Head & Shoulders)", "Düşüş"
            
    # TOBO (Inverse H&S)
    if len(recent_troughs) >= 3:
        t1, t2, t3 = closes[recent_troughs[-3]], closes[recent_troughs[-2]], closes[recent_troughs[-1]]
        if t2 < t1 and t2 < t3 and abs(t1 - t3) / t1 < 0.03:
            return "TOBO (Ters OBO)", "Yükseliş"
            
    # Triangles (Higher lows, lower highs)
    if len(recent_peaks) >= 2 and len(recent_troughs) >= 2:
        p1, p2 = closes[recent_peaks[-2]], closes[recent_peaks[-1]]
        t1, t2 = closes[recent_troughs[-2]], closes[recent_troughs[-1]]
        if p2 < p1 and t2 > t1:
            return "Simetrik Üçgen (Daralan)", "Belirsiz / Kırılım Bekleniyor"
        if abs(p1 - p2)/p1 < 0.02 and t2 > t1:
            return "Yükselen Üçgen", "Yükseliş"
        if p2 < p1 and abs(t1 - t2)/t1 < 0.02:
            return "Alçalan Üçgen", "Düşüş"

    # Fallback to trend
    current_price = closes[-1]
    sma50 = df['SMA_50'].iloc[-1]
    sma200 = df['SMA_200'].iloc[-1]
    if current_price > sma50 and current_price > sma200:
        return "Yükseliş Trendi (SMA Üzeri)", "Yükseliş"
    elif current_price < sma50 and current_price < sma200:
        return "Düşüş Trendi (SMA Altı)", "Düşüş"
        
    return None, None

def scan_markets(limit=50, interval='1h'):
    symbols = get_top_coins(limit)
    results = []
    
    for symbol in symbols:
        df = get_klines(symbol, interval, limit=200) # Need 200 for SMA200
        if df.empty: continue
        
        df = calculate_indicators(df)
        peaks, troughs = find_extrema(df, order=5)
        support, resistance = find_support_resistance(df, peaks, troughs)
        formation, direction = detect_advanced_patterns(df, peaks, troughs)
        
        if formation:
            # Prepare chart data to send to frontend
            # We will send the last 100 candles to keep the payload reasonable
            df_chart = df.tail(100).copy()
            
            # Format data for Lightweight Charts
            # Time must be in string 'YYYY-MM-DD' or unix timestamp in seconds
            candle_data = []
            rsi_data = []
            sma20_data = []
            sma50_data = []
            
            for index, row in df_chart.iterrows():
                time_val = int(row['timestamp'].timestamp())
                candle_data.append({
                    'time': time_val,
                    'open': row['open'],
                    'high': row['high'],
                    'low': row['low'],
                    'close': row['close']
                })
                rsi_data.append({'time': time_val, 'value': row['RSI']})
                sma20_data.append({'time': time_val, 'value': row['SMA_20']})
                sma50_data.append({'time': time_val, 'value': row['SMA_50']})

            results.append({
                "coin": symbol.replace('USDT', ''),
                "exchange": "Binance",
                "timeframe": interval,
                "formation": formation,
                "direction": direction,
                "support": round(support, 4) if support else None,
                "resistance": round(resistance, 4) if resistance else None,
                "chartData": {
                    "candles": candle_data,
                    "rsi": rsi_data,
                    "sma20": sma20_data,
                    "sma50": sma50_data
                }
            })
            
    return results
