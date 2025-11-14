from flask import Flask, request, jsonify
import os
import requests
import json
from datetime import datetime
from influxdb import InfluxDBClient
import pandas as pd
import numpy as np

app = Flask(__name__)

# =========================
# Configuration (from env)
# =========================

INFLUXDB_HOST = os.getenv("INFLUXDB_HOST", "localhost")
INFLUXDB_PORT = int(os.getenv("INFLUXDB_PORT", "8086"))
INFLUXDB_DATABASE = os.getenv("INFLUXDB_DATABASE", "trading_data")

COINBASE_API_BASE = "https://api.coinbase.com/v3"
COINBASE_API_KEY = os.getenv("COINBASE_API_KEY")          
COINBASE_API_SECRET = os.getenv("COINBASE_API_SECRET")    
WEBHOOK_TOKEN = os.getenv("WEBHOOK_TOKEN")               

# Demo Mode
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"

# =========================
# InfluxDB Client
# =========================

client = InfluxDBClient(host=INFLUXDB_HOST, port=INFLUXDB_PORT)
client.switch_database(INFLUXDB_DATABASE)

# =========================
# Helper functions
# =========================

def fetch_trading_data():
    """Bring Coinbase Crypto Pair Data"""
    if not COINBASE_API_KEY:
        app.logger.warning("COINBASE_API_KEY not set.")
        return None

    try:
        response = requests.get(
            f"{COINBASE_API_BASE}/products",
            headers={"Authorization": f"Bearer {COINBASE_API_KEY}"}
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error fetching trading data: {e}")
        return None


def calculate_rsi(data, length):
    delta = data["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=length).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=length).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_bollinger_bands(data, length, multiplier):
    ma = data["close"].rolling(window=length).mean()
    std = data["close"].rolling(window=length).std()
    upper_band = ma + (multiplier * std)
    lower_band = ma - (multiplier * std)
    return upper_band, lower_band


def calculate_atr(data, length):
    high_low = data["high"] - data["low"]
    high_close = np.abs(data["high"] - data["close"].shift())
    low_close = np.abs(data["low"] - data["close"].shift())
    tr = high_low.combine(high_close, max).combine(low_close, max)
    atr = tr.rolling(window=length).mean()
    return atr


def calculate_supertrend(data, atr_length, multiplier):
    atr = calculate_atr(data, atr_length)
    hl2 = (data["high"] + data["low"]) / 2
    upper_band = hl2 + (multiplier * atr)
    lower_band = hl2 - (multiplier * atr)
    return upper_band, lower_band


def calculate_strategies_dynamic(params):
    query = "SELECT * FROM trading_metrics WHERE time > now() - 3d"
    results = client.query(query)
    points = list(results.get_points())
    df = pd.DataFrame(points)

    if df.empty:
        return {}

    rsi = calculate_rsi(df, length=params.get("RSI_Length", 14))
    upper_bb, lower_bb = calculate_bollinger_bands(
        df,
        length=params.get("Bollinger_Bands_Length", 20),
        multiplier=params.get("Bollinger_Bands_Multiplier", 2),
    )
    atr = calculate_atr(df, length=params.get("ATR_Length", 14))
    upper_st, lower_st = calculate_supertrend(
        df,
        atr_length=params.get("Supertrend_ATR_Length", 10),
        multiplier=params.get("Supertrend_ATR_Multiplier", 3),
    )

    strategies = {
        "RSI": rsi.iloc[-1] if not rsi.empty else None,
        "BB_Upper": upper_bb.iloc[-1] if not upper_bb.empty else None,
        "BB_Lower": lower_bb.iloc[-1] if not lower_bb.empty else None,
        "ATR": atr.iloc[-1] if not atr.empty else None,
        "Supertrend_Upper": upper_st.iloc[-1] if not upper_st.empty else None,
        "Supertrend_Lower": lower_st.iloc[-1] if not lower_st.empty else None,
    }
    return strategies


def verify_webhook_secret(payload: dict) -> bool:

    if not WEBHOOK_TOKEN:
        return True
    return payload.get("token") == WEBHOOK_TOKEN

# =========================
# Routes
# =========================

@app.route("/webhook", methods=["POST"])
def handle_webhook():
    payload = request.json
    if not payload:
        return jsonify({"error": "Invalid payload"}), 400

    # Verify Webhook 
    if not verify_webhook_secret(payload):
        app.logger.warning("Invalid webhook token")
        return jsonify({"error": "Unauthorized"}), 401

    # Log payload to InfluxDB
    timestamp = datetime.utcnow().isoformat()
    json_body = [
        {
            "measurement": "webhook_data",
            "tags": {"source": "tradingview"},
            "time": timestamp,
            "fields": payload,
        }
    ]
    client.write_points(json_body)

    strategies = calculate_strategies_dynamic(payload)

    return jsonify({"status": "success", "strategies": strategies}), 200


@app.route("/wallet", methods=["GET"])
def get_wallet_info():
    if not COINBASE_API_KEY:
        return jsonify({"error": "COINBASE_API_KEY not configured"}), 500

    url = f"{COINBASE_API_BASE}/accounts"
    headers = {
        "Authorization": f"Bearer {COINBASE_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return jsonify(response.json()), 200
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error fetching wallet information: {e}")
        return jsonify({"error": "Unable to fetch wallet information"}), 500


@app.route("/trade", methods=["POST"])
def place_limit_trade():
    payload = request.json
    if not payload:
        return jsonify({"error": "Invalid payload"}), 400

    side = payload.get("side")  # buy or sell
    product_id = payload.get("product_id", "BTC-USD")
    size = payload.get("size", 0.01)
    price = payload.get("price")

    if not side or price is None:
        return jsonify({"error": "Missing required fields: 'side' or 'price'"}), 400

    order_payload = {
        "side": side,
        "product_id": product_id,
        "size": size,
        "price": price,
        "type": "limit",
    }

    if DEMO_MODE:
        # Only Log
        app.logger.info(f"[DEMO_MODE] Order payload: {order_payload}")
        return jsonify({"status": "demo", "order": order_payload}), 200

    if not COINBASE_API_KEY:
        return jsonify({"error": "COINBASE_API_KEY not configured"}), 500

    url = f"{COINBASE_API_BASE}/orders"
    headers = {
        "Authorization": f"Bearer {COINBASE_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        response = requests.post(url, headers=headers, data=json.dumps(order_payload), timeout=10)
        response.raise_for_status()
        return jsonify(response.json()), 200
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error placing limit trade: {e}")
        return jsonify({"error": "Unable to place limit trade"}), 500


@app.route("/update_strategies", methods=["GET"])
def update_strategies():
    default_params = {
        "RSI_Length": 14,
        "Bollinger_Bands_Length": 20,
        "Bollinger_Bands_Multiplier": 2,
        "ATR_Length": 14,
        "Supertrend_ATR_Length": 10,
        "Supertrend_ATR_Multiplier": 3,
    }
    strategies = calculate_strategies_dynamic(default_params)
    timestamp = datetime.utcnow().isoformat()

    json_body = [
        {
            "measurement": "trading_strategies",
            "time": timestamp,
            "fields": strategies,
        }
    ]
    client.write_points(json_body)

    return jsonify({"status": "updated", "strategies": strategies}), 200


if __name__ == "__main__":
    databases = client.get_list_database()
    if not any(db["name"] == INFLUXDB_DATABASE for db in databases):
        client.create_database(INFLUXDB_DATABASE)

    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
