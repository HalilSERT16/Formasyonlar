import os
from flask import Flask, render_template, jsonify, request, send_from_directory
import scanner

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.png', mimetype='image/png')

@app.route('/api/scan')
def api_scan():
    try:
        limit = int(request.args.get('limit', 50))
        interval = request.args.get('interval', '1h')
        
        # Optional mapping from UI to Binance intervals
        # '1 Saat' -> '1h', '4 Saat' -> '4h'
        interval_mapping = {
            '15m': '15m',
            '1 Saat': '1h',
            '4 Saat': '4h',
            '1 Gün': '1d'
        }
        
        binance_interval = interval_mapping.get(interval, '1h')

        # Eğer kullanıcı arama terimi girdiyse sadece o coinleri tara
        search = request.args.get('search', '').strip().upper()
        specific_symbols = None
        if search:
            # "BTC ETH" veya "BTC,ETH" formatını da destekle
            tokens = search.replace(',', ' ').split()
            specific_symbols = [t if t.endswith('USDT') else t + 'USDT' for t in tokens if t]

        results = scanner.scan_markets(limit=limit, interval=binance_interval, symbols=specific_symbols)
        return jsonify(results)
    except Exception as e:
        import traceback
        return jsonify({"error": f"Sunucu hatası: {str(e)}", "trace": traceback.format_exc()}), 500


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint bulunamadı"}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Sunucu iç hatası"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
