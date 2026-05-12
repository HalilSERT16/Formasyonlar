from flask import Flask, render_template, jsonify, request
import scanner

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/scan')
def api_scan():
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
    
    results = scanner.scan_markets(limit=limit, interval=binance_interval)
    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
