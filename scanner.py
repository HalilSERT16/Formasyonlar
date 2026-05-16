import requests
import pandas as pd
import numpy as np

BINANCE_API_URL = "https://data-api.binance.vision/api/v3"

def get_top_coins(limit=50):
    try:
        url = f"{BINANCE_API_URL}/ticker/24hr"
        response = requests.get(url, timeout=10)
        response.raise_for_status() # Raise error for 403, 429, etc.
        data = response.json()
        usdt_pairs = [d for d in data if d['symbol'].endswith('USDT')]
        usdt_pairs.sort(key=lambda x: float(x['quoteVolume']), reverse=True)
        return [pair['symbol'] for pair in usdt_pairs[:limit]], None
    except Exception as e:
        return [], str(e)

def get_klines(symbol, interval, limit=200):
    try:
        url = f"{BINANCE_API_URL}/klines"
        params = {'symbol': symbol, 'interval': interval, 'limit': limit}
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'qav', 'num_trades', 'tbbav', 'tbqav', 'ignore'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        return df
    except Exception as e:
        return pd.DataFrame()

def calculate_rsi(series, period=14):
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ema_up = up.ewm(com=period - 1, adjust=False).mean()
    ema_down = down.ewm(com=period - 1, adjust=False).mean()
    rs = ema_up / ema_down
    return 100 - (100 / (1 + rs))

def calculate_indicators(df):
    if df.empty or len(df) < 20: return df
    
    # Calculate RSI
    df['RSI'] = calculate_rsi(df['close'], 14)
    
    # Calculate MAs
    df['SMA_20'] = df['close'].rolling(window=20).mean()
    df['SMA_50'] = df['close'].rolling(window=50).mean()
    df['SMA_200'] = df['close'].rolling(window=200).mean()
    
    df.bfill(inplace=True)
    return df

def find_extrema(df, order=5):
    closes = df['close'].values
    peaks = []
    troughs = []
    
    for i in range(order, len(closes) - order):
        if np.max(closes[i-order:i+order+1]) == closes[i]:
            peaks.append(i)
        if np.min(closes[i-order:i+order+1]) == closes[i]:
            troughs.append(i)
            
    return peaks, troughs

def find_support_resistance(df, peaks, troughs):
    highs = df['high'].values
    lows = df['low'].values
    
    resistance = np.max([highs[p] for p in peaks[-3:]]) if len(peaks) >= 3 else (highs[peaks[-1]] if peaks else None)
    support = np.min([lows[t] for t in troughs[-3:]]) if len(troughs) >= 3 else (lows[troughs[-1]] if troughs else None)
    
    return support, resistance

def detect_advanced_patterns(df, peaks, troughs):
    if len(peaks) < 2 or len(troughs) < 2:
        return None, None
        
    closes = df['close'].values
    
    recent_peaks = peaks[-3:]
    recent_troughs = troughs[-3:]
    
    if len(recent_peaks) >= 2:
        p1, p2 = closes[recent_peaks[-2]], closes[recent_peaks[-1]]
        if abs(p1 - p2) / p1 < 0.02:
            return "İkili Tepe (Double Top)", "Düşüş"
            
    if len(recent_troughs) >= 2:
        t1, t2 = closes[recent_troughs[-2]], closes[recent_troughs[-1]]
        if abs(t1 - t2) / t1 < 0.02:
            return "İkili Dip (Double Bottom)", "Yükseliş"

    if len(recent_peaks) >= 3:
        p1, p2, p3 = closes[recent_peaks[-3]], closes[recent_peaks[-2]], closes[recent_peaks[-1]]
        if p2 > p1 and p2 > p3 and abs(p1 - p3) / p1 < 0.03:
            return "OBO (Head & Shoulders)", "Düşüş"
            
    if len(recent_troughs) >= 3:
        t1, t2, t3 = closes[recent_troughs[-3]], closes[recent_troughs[-2]], closes[recent_troughs[-1]]
        if t2 < t1 and t2 < t3 and abs(t1 - t3) / t1 < 0.03:
            return "TOBO (Ters OBO)", "Yükseliş"
            
    if len(recent_peaks) >= 2 and len(recent_troughs) >= 2:
        p1, p2 = closes[recent_peaks[-2]], closes[recent_peaks[-1]]
        t1, t2 = closes[recent_troughs[-2]], closes[recent_troughs[-1]]
        if p2 < p1 and t2 > t1:
            return "Simetrik Üçgen (Daralan)", "Belirsiz / Kırılım Bekleniyor"
        if abs(p1 - p2)/p1 < 0.02 and t2 > t1:
            return "Yükselen Üçgen", "Yükseliş"
        if p2 < p1 and abs(t1 - t2)/t1 < 0.02:
            return "Alçalan Üçgen", "Düşüş"

    current_price = closes[-1]
    sma50 = df['SMA_50'].iloc[-1] if not np.isnan(df['SMA_50'].iloc[-1]) else 0
    sma200 = df['SMA_200'].iloc[-1] if not np.isnan(df['SMA_200'].iloc[-1]) else 0
    
    if sma50 and sma200:
        if current_price > sma50 and current_price > sma200:
            return "Yükseliş Trendi (SMA Üzeri)", "Yükseliş"
        elif current_price < sma50 and current_price < sma200:
            return "Düşüş Trendi (SMA Altı)", "Düşüş"
        
    return None, None

def scan_markets(limit=50, interval='1h', symbols=None):
    try:
        if symbols:
            # Kullanıcı belirli coin(ler) girdi — sadece onları tara
            pass
        else:
            symbols, err = get_top_coins(limit)
            if err or not symbols:
                return {"error": f"Binance API'ye ulaşılamadı (Railway IP bloku veya Timeout). Detay: {err}"}
            
        results = []
        specific_search = bool(symbols)  # Kullanıcı belirli coin girdiyse True

        for symbol in symbols:
            df = get_klines(symbol, interval, limit=200)
            if df.empty:
                if specific_search:
                    results.append({
                        "coin": symbol.replace('USDT', ''),
                        "exchange": "Binance",
                        "timeframe": interval,
                        "formation": "Veri Alınamadı",
                        "direction": "-",
                        "support": None,
                        "resistance": None,
                        "chartData": {"candles": [], "rsi": [], "sma20": [], "sma50": []}
                    })
                continue

            df = calculate_indicators(df)
            peaks, troughs = find_extrema(df, order=5)
            support, resistance = find_support_resistance(df, peaks, troughs)
            formation, direction = detect_advanced_patterns(df, peaks, troughs)

            # Belirli coin aranıyorsa formasyon bulunamasa da göster
            if formation or specific_search:
                df_chart = df.tail(100).copy()
                candle_data = []
                rsi_data = []
                sma20_data = []
                sma50_data = []
                
                for index, row in df_chart.iterrows():
                    time_val = int(row['timestamp'].timestamp())
                    candle_data.append({'time': time_val, 'open': row['open'], 'high': row['high'], 'low': row['low'], 'close': row['close']})
                    
                    rsi_val = row.get('RSI', 0)
                    rsi_data.append({'time': time_val, 'value': rsi_val if not pd.isna(rsi_val) else 0})
                    
                    sma20_val = row.get('SMA_20', row['close'])
                    sma20_data.append({'time': time_val, 'value': sma20_val if not pd.isna(sma20_val) else row['close']})
                    
                    sma50_val = row.get('SMA_50', row['close'])
                    sma50_data.append({'time': time_val, 'value': sma50_val if not pd.isna(sma50_val) else row['close']})

                results.append({
                    "coin": symbol.replace('USDT', ''),
                    "exchange": "Binance",
                    "timeframe": interval,
                    "formation": formation or "Belirgin Formasyon Yok",
                    "direction": direction or "-",
                    "support": round(support, 4) if support else None,
                    "resistance": round(resistance, 4) if resistance else None,
                    "chartData": {
                        "candles": candle_data,
                        "rsi": rsi_data,
                        "sma20": sma20_data,
                        "sma50": sma50_data
                    }
                })
                
        return {"data": results}
    except Exception as e:
        import traceback
        return {"error": f"Tarama sırasında kritik hata oluştu: {str(e)}", "trace": traceback.format_exc()}
