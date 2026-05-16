import requests
import pandas as pd
import numpy as np

BINANCE_API_URL = "https://data-api.binance.vision/api/v3"
STABLECOINS = ['USDCUSDT', 'FDUSDUSDT', 'TUSDUSDT', 'DAIUSDT', 'USDPUSDT', 'AEURUSDT', 'BUSDUSDT', 'USDEUSDT', 'EURUSDT', 'GBPUSDT', 'USDSUSDT']


def get_top_coins(limit=50):
    try:
        url = f"{BINANCE_API_URL}/ticker/24hr"
        response = requests.get(url, timeout=10)
        response.raise_for_status() # Raise error for 403, 429, etc.
        data = response.json()
        usdt_pairs = [d for d in data if d['symbol'].endswith('USDT') and d['symbol'] not in STABLECOINS]
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



def find_extrema(df, order=5):
    highs = df['high'].values
    lows = df['low'].values
    peaks = []
    troughs = []
    
    for i in range(order, len(df) - order):
        if np.max(highs[i-order:i+order+1]) == highs[i]:
            peaks.append(i)
        if np.min(lows[i-order:i+order+1]) == lows[i]:
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
        return None, None, []
        
    closes = df['close'].values
    highs = df['high'].values
    lows = df['low'].values
    timestamps = df['timestamp'].values
    
    def get_point(idx, p_type='close'):
        val = highs[idx] if p_type == 'high' else (lows[idx] if p_type == 'low' else closes[idx])
        return {'time': int(pd.Timestamp(timestamps[idx]).timestamp()), 'value': float(val)}

    recent_peaks = peaks[-4:]
    recent_troughs = troughs[-4:]
    
    # Üçlü Tepe (Triple Top)
    if len(recent_peaks) >= 3:
        p1_idx, p2_idx, p3_idx = recent_peaks[-3], recent_peaks[-2], recent_peaks[-1]
        p1, p2, p3 = highs[p1_idx], highs[p2_idx], highs[p3_idx]
        if max(p1, p2, p3) - min(p1, p2, p3) < 0.015 * min(p1, p2, p3):
            return "Üçlü Tepe (Triple Top)", "Düşüş", [get_point(p1_idx, 'high'), get_point(p2_idx, 'high'), get_point(p3_idx, 'high')]

    # Üçlü Dip (Triple Bottom)
    if len(recent_troughs) >= 3:
        t1_idx, t2_idx, t3_idx = recent_troughs[-3], recent_troughs[-2], recent_troughs[-1]
        t1, t2, t3 = lows[t1_idx], lows[t2_idx], lows[t3_idx]
        if max(t1, t2, t3) - min(t1, t2, t3) < 0.015 * min(t1, t2, t3):
            return "Üçlü Dip (Triple Bottom)", "Yükseliş", [get_point(t1_idx, 'low'), get_point(t2_idx, 'low'), get_point(t3_idx, 'low')]

    # İkili Tepe
    if len(recent_peaks) >= 2:
        p1_idx, p2_idx = recent_peaks[-2], recent_peaks[-1]
        p1, p2 = highs[p1_idx], highs[p2_idx]
        if abs(p1 - p2) / p1 < 0.018:
            return "İkili Tepe (Double Top)", "Düşüş", [get_point(p1_idx, 'high'), get_point(p2_idx, 'high')]
            
    # İkili Dip
    if len(recent_troughs) >= 2:
        t1_idx, t2_idx = recent_troughs[-2], recent_troughs[-1]
        t1, t2 = lows[t1_idx], lows[t2_idx]
        if abs(t1 - t2) / t1 < 0.018:
            return "İkili Dip (Double Bottom)", "Yükseliş", [get_point(t1_idx, 'low'), get_point(t2_idx, 'low')]

    # OBO (Head & Shoulders)
    if len(recent_peaks) >= 3 and len(recent_troughs) >= 2:
        p1_idx, p2_idx, p3_idx = recent_peaks[-3], recent_peaks[-2], recent_peaks[-1]
        p1, p2, p3 = highs[p1_idx], highs[p2_idx], highs[p3_idx]
        if p2 > p1 and p2 > p3 and abs(p1 - p3) / p1 < 0.035:
            return "OBO (Head & Shoulders)", "Düşüş", [get_point(p1_idx, 'high'), get_point(p2_idx, 'high'), get_point(p3_idx, 'high')]
            
    # TOBO (Ters OBO)
    if len(recent_troughs) >= 3 and len(recent_peaks) >= 2:
        t1_idx, t2_idx, t3_idx = recent_troughs[-3], recent_troughs[-2], recent_troughs[-1]
        t1, t2, t3 = lows[t1_idx], lows[t2_idx], lows[t3_idx]
        if t2 < t1 and t2 < t3 and abs(t1 - t3) / t1 < 0.035:
            return "TOBO (Ters OBO)", "Yükseliş", [get_point(t1_idx, 'low'), get_point(t2_idx, 'low'), get_point(t3_idx, 'low')]
            
    # Fincan Kulp & Ters Fincan Kulp
    if len(recent_peaks) >= 3 and len(recent_troughs) >= 2:
        p1_idx, p2_idx = recent_peaks[-3], recent_peaks[-2]
        p1, p2 = highs[p1_idx], highs[p2_idx]
        if abs(p1 - p2)/p1 < 0.025 and recent_peaks[-1] > p2_idx:
            # P1 ve P2 arası fincan, son tepe kulp
            return "Fincan Kulp (Cup & Handle)", "Yükseliş", [get_point(p1_idx, 'high'), get_point(p2_idx, 'high'), get_point(recent_peaks[-1], 'high')]

    # Dikdörtgen / Kanal (Rectangle)
    if len(recent_peaks) >= 2 and len(recent_troughs) >= 2:
        p1, p2 = highs[recent_peaks[-2]], highs[recent_peaks[-1]]
        t1, t2 = lows[recent_troughs[-2]], lows[recent_troughs[-1]]
        if abs(p1 - p2)/p1 < 0.015 and abs(t1 - t2)/t1 < 0.015:
            pts = [get_point(recent_peaks[-2], 'high'), get_point(recent_troughs[-2], 'low'), get_point(recent_peaks[-1], 'high'), get_point(recent_troughs[-1], 'low')]
            pts.sort(key=lambda x: x['time'])
            return "Dikdörtgen Kanal (Rectangle)", "Yatay / Kırılım Bekleniyor", pts

    # Üçgenler, Kamalar, Bayrak & Flama
    if len(recent_peaks) >= 2 and len(recent_troughs) >= 2:
        p1_idx, p2_idx = recent_peaks[-2], recent_peaks[-1]
        t1_idx, t2_idx = recent_troughs[-2], recent_troughs[-1]
        p1, p2 = highs[p1_idx], highs[p2_idx]
        t1, t2 = lows[t1_idx], lows[t2_idx]
        
        pts = [get_point(p1_idx, 'high'), get_point(t1_idx, 'low'), get_point(p2_idx, 'high'), get_point(t2_idx, 'low')]
        pts.sort(key=lambda x: x['time'])

        # Kamalar (Wedges)
        if p2 < p1 and t2 < t1:
            # Alçalan Kama (Falling Wedge) - Diplerin eğimi tepelerden daha yataysa veya tam tersi daralıyorsa
            slope_p = (p2 - p1) / (p2_idx - p1_idx)
            slope_t = (t2 - t1) / (t2_idx - t1_idx)
            if abs(slope_p) > abs(slope_t):
                return "Alçalan Kama (Falling Wedge)", "Yükseliş", pts
            else:
                return "Düşen Bayrak / Kanal (Bearish Flag)", "Düşüş", pts
                
        if p2 > p1 and t2 > t1:
            # Yükselen Kama (Rising Wedge)
            slope_p = (p2 - p1) / (p2_idx - p1_idx)
            slope_t = (t2 - t1) / (t2_idx - t1_idx)
            if abs(slope_t) > abs(slope_p):
                return "Yükselen Kama (Rising Wedge)", "Düşüş", pts
            else:
                return "Yükselen Bayrak / Kanal (Bullish Flag)", "Yükseliş", pts

        # Üçgenler (Triangles) & Flamalar (Pennants)
        if p2 < p1 and t2 > t1:
            # Kısa sürede oluşmuşsa Flama, uzun süredeyse Simetrik Üçgen
            if abs(p2_idx - p1_idx) < 15:
                return "Flama (Pennant)", "Devam Formasyonu", pts
            return "Simetrik Üçgen (Daralan)", "Belirsiz / Kırılım Bekleniyor", pts
            
        if abs(p1 - p2)/p1 < 0.015 and t2 > t1:
            return "Yükselen Üçgen (Ascending Triangle)", "Yükseliş", pts
            
        if p2 < p1 and abs(t1 - t2)/t1 < 0.015:
            return "Alçalan Üçgen (Descending Triangle)", "Düşüş", pts

    return None, None, []

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
                continue


            peaks, troughs = find_extrema(df, order=5)
            support, resistance = find_support_resistance(df, peaks, troughs)
            formation, direction, pattern_points = detect_advanced_patterns(df, peaks, troughs)

            # Belirli coin aranıyorsa formasyon bulunamasa da göster
            # Sadece formasyon bulunan coinleri listele
            if formation:
                df_chart = df.tail(100).copy()
                candle_data = []
                for index, row in df_chart.iterrows():
                    time_val = int(row['timestamp'].timestamp())
                    candle_data.append({'time': time_val, 'open': row['open'], 'high': row['high'], 'low': row['low'], 'close': row['close']})

                # Collect all peak/trough markers for the chart
                markers = []
                for p_idx in peaks:
                    if p_idx >= max(0, len(df) - 100):
                        markers.append({
                            'time': int(df.iloc[p_idx]['timestamp'].timestamp()),
                            'position': 'aboveBar',
                            'color': '#ef5350',
                            'shape': 'arrowDown',
                            'text': 'Tepe'
                        })
                for t_idx in troughs:
                    if t_idx >= max(0, len(df) - 100):
                        markers.append({
                            'time': int(df.iloc[t_idx]['timestamp'].timestamp()),
                            'position': 'belowBar',
                            'color': '#26a69a',
                            'shape': 'arrowUp',
                            'text': 'Dip'
                        })

                results.append({
                    "coin": symbol.replace('USDT', ''),
                    "exchange": "Binance",
                    "timeframe": interval,
                    "formation": formation,
                    "direction": direction or "-",
                    "support": round(support, 4) if support else None,
                    "resistance": round(resistance, 4) if resistance else None,
                    "chartData": {
                        "candles": candle_data,
                        "patternPoints": pattern_points,
                        "markers": markers
                    }
                })
                
        return {"data": results}
    except Exception as e:
        import traceback
        return {"error": f"Tarama sırasında kritik hata oluştu: {str(e)}", "trace": traceback.format_exc()}
