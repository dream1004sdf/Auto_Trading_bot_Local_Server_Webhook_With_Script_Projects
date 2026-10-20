"""Portfolio-safe TradingView webhook and technical indicator service.

Real brokerage orders are deliberately NOT supported in this public demo.
The historical experiments remain accessible through repository history.
"""
from __future__ import annotations

import hmac
import json
import math
import os
import re
from datetime import datetime, timezone
from typing import Any

import pandas as pd
from flask import Flask, jsonify, request

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024

DEFAULT_PARAMS = {
    "RSI_Length": 14,
    "Bollinger_Bands_Length": 20,
    "Bollinger_Bands_Multiplier": 2.0,
    "ATR_Length": 14,
    "Supertrend_ATR_Length": 10,
    "Supertrend_ATR_Multiplier": 3.0,
}
SENSITIVE_FIELDS = {"token", "api_key", "api_secret", "password", "secret", "authorization"}


def env_flag(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"true", "1", "yes"}


def clean_number(value: Any) -> float | None:
    try:
        result = float(value)
    except (ValueError, TypeError):
        return None
    return result if math.isfinite(result) else None


def calculate_rsi(data: pd.DataFrame, length: int = 14) -> pd.Series:
    """Simple-moving-average RSI, as in the original prototype."""
    change = data["close"].diff()
    gain = change.clip(lower=0).rolling(length, min_periods=length).mean()
    loss = (-change.clip(upper=0)).rolling(length, min_periods=length).mean()
    ratio = gain / loss.replace(0, float("nan"))
    rsi = 100 - 100 / (1 + ratio)
    rsi = rsi.mask((loss == 0) & (gain > 0), 100.0)
    return rsi.mask((loss == 0) & (gain == 0), 50.0)


def calculate_bollinger_bands(data: pd.DataFrame, length: int = 20, multiplier: float = 2.0):
    center = data["close"].rolling(length, min_periods=length).mean()
    deviation = data["close"].rolling(length, min_periods=length).std()
    return center + multiplier * deviation, center - multiplier * deviation


def calculate_atr(data: pd.DataFrame, length: int = 14) -> pd.Series:
    """Simple-moving-average ATR."""
    previous_close = data["close"].shift()
    ranges = pd.concat([
        data["high"] - data["low"],
        (data["high"] - previous_close).abs(),
        (data["low"] - previous_close).abs(),
    ], axis=1).max(axis=1)
    return ranges.rolling(length, min_periods=length).mean()


def calculate_supertrend_bands(data: pd.DataFrame, length: int = 10, multiplier: float = 3.0):
    """Basic ATR bands ONLY, not a complete trend-switching Supertrend indicator."""
    atr = calculate_atr(data, length)
    midpoint = (data["high"] + data["low"]) / 2
    return midpoint + multiplier * atr, midpoint - multiplier * atr


def calculate_indicators(data: pd.DataFrame, params: dict[str, Any] | None = None):
    if data.empty or not {"high", "low", "close"}.issubset(data.columns):
        return {}
    values = DEFAULT_PARAMS | (params or {})
    for key in ("RSI_Length", "Bollinger_Bands_Length", "ATR_Length", "Supertrend_ATR_Length"):
        if not isinstance(values[key], int) or isinstance(values[key], bool) or not 1 <= values[key] <= 500:
            raise ValueError(f"Invalid period: {key}")
    for key in ("Bollinger_Bands_Multiplier", "Supertrend_ATR_Multiplier"):
        value = clean_number(values[key])
        if value is None or not 0 < value <= 100:
            raise ValueError(f"Invalid multiplier: {key}")
        values[key] = value
    data = data.copy()
    if "time" in data.columns:
        data = data.sort_values("time")
    for column in ("high", "low", "close"):
        data[column] = pd.to_numeric(data[column], errors="coerce")
    data = data.dropna(subset=["high", "low", "close"])
    if data.empty:
        return {}
    rsi = calculate_rsi(data, values["RSI_Length"])
    upper_bb, lower_bb = calculate_bollinger_bands(
        data, values["Bollinger_Bands_Length"], values["Bollinger_Bands_Multiplier"]
    )
    atr = calculate_atr(data, values["ATR_Length"])
    upper_st, lower_st = calculate_supertrend_bands(
        data, values["Supertrend_ATR_Length"], values["Supertrend_ATR_Multiplier"]
    )
    return {
        "RSI": clean_number(rsi.iloc[-1]),
        "BB_Upper": clean_number(upper_bb.iloc[-1]),
        "BB_Lower": clean_number(lower_bb.iloc[-1]),
        "ATR": clean_number(atr.iloc[-1]),
        "Supertrend_Band_Upper": clean_number(upper_st.iloc[-1]),
        "Supertrend_Band_Lower": clean_number(lower_st.iloc[-1]),
    }


def influx_enabled() -> bool:
    return env_flag("INFLUXDB_ENABLED")


def get_influx_client():
    """Connect to InfluxDB 1.x only when explicitly enabled."""
    from influxdb import InfluxDBClient
    client = InfluxDBClient(
        host=os.getenv("INFLUXDB_HOST", "localhost"),
        port=int(os.getenv("INFLUXDB_PORT", "8086")),
        timeout=3,
    )
    database = os.getenv("INFLUXDB_DATABASE", "trading_data")
    names = {item["name"] for item in client.get_list_database()}
    if database not in names:
        client.create_database(database)
    client.switch_database(database)
    return client


def query_indicators(client):
    """OHLC measurement is supplied separately, not inferred from webhook signals."""
    rows = list(client.query(
        "SELECT time,high,low,close FROM trading_metrics "
        "WHERE time > now() - 3d ORDER BY time ASC"
    ).get_points())
    return calculate_indicators(pd.DataFrame(rows))


def verify_webhook_token(payload: dict[str, Any]) -> bool:
    configured = os.getenv("WEBHOOK_TOKEN", "")
    if not configured:
        # Convenient for localhost demonstration; unsafe on the public internet.
        return True
    supplied = request.headers.get("X-Webhook-Token") or payload.get("token", "")
    return isinstance(supplied, str) and hmac.compare_digest(supplied, configured)


def safe_fields(payload: dict[str, Any]) -> dict[str, Any]:
    """Exclude credentials and transform nested payloads into database-safe fields."""
    fields = {}
    for key, value in payload.items():
        if not isinstance(key, str) or key.lower() in SENSITIVE_FIELDS:
            continue
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}", key):
            continue
        if value is None:
            continue
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        elif not isinstance(value, (str, bool, int, float)):
            continue
        if isinstance(value, float) and not math.isfinite(value):
            continue
        fields[key] = value
    return fields


@app.get("/health")
def health():
    return jsonify({"status": "ok", "demo_mode": True, "influxdb_enabled": influx_enabled()})


@app.post("/webhook")
def webhook():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or not payload:
        return jsonify({"error": "Expected a nonempty JSON object"}), 400
    if not verify_webhook_token(payload):
        return jsonify({"error": "Unauthorized"}), 401
    fields = safe_fields(payload)
    if not fields:
        return jsonify({"error": "No safe event fields provided"}), 400
    if not influx_enabled():
        return jsonify({
            "status": "accepted", "stored": False, "mode": "demo",
            "message": "InfluxDB disabled; event validated but not persisted",
            "indicators": {},
        }), 200
    try:
        client = get_influx_client()
        client.write_points([{
            "measurement": "webhook_data",
            "tags": {"source": "tradingview"},
            "time": datetime.now(timezone.utc).isoformat(),
            "fields": fields,
        }])
        indicators = query_indicators(client)
    except Exception:
        app.logger.exception("Webhook persistence or indicator calculation failed")
        return jsonify({"error": "Data service unavailable"}), 503
    return jsonify({"status": "accepted", "stored": True, "mode": "demo", "indicators": indicators}), 200


@app.post("/trade")
def trade():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Expected a JSON object"}), 400
    side = payload.get("side")
    product_id = payload.get("product_id", "BTC-USD")
    size = clean_number(payload.get("size"))
    price = clean_number(payload.get("price"))
    if (
        side not in {"buy", "sell"}
        or not isinstance(product_id, str)
        or not re.fullmatch(r"[A-Z0-9-]{3,30}", product_id)
        or size is None or size <= 0
        or price is None or price <= 0
    ):
        return jsonify({"error": "Valid side (buy/sell), product_id, size, and price required"}), 400
    # Deliberately no network call to a brokerage.
    return jsonify({
        "status": "simulated", "live_order_submitted": False,
        "order": {
            "side": side, "product_id": product_id,
            "size": size, "price": price, "type": "limit",
        },
    }), 200


@app.get("/wallet")
def wallet():
    return jsonify({"error": "Live account access is not supported in the public demo"}), 501


@app.get("/update_strategies")
def update_strategies():
    if not influx_enabled():
        return jsonify({"error": "Enable InfluxDB and supply trading_metrics data"}), 503
    try:
        client = get_influx_client()
        indicators = query_indicators(client)
        clean = {k: v for k, v in indicators.items() if v is not None}
        if clean:
            client.write_points([{
                "measurement": "trading_strategies",
                "time": datetime.now(timezone.utc).isoformat(),
                "fields": clean,
            }])
    except Exception:
        app.logger.exception("Indicator refresh failed")
        return jsonify({"error": "Data service unavailable"}), 503
    return jsonify({"status": "updated", "indicators": indicators}), 200


if __name__ == "__main__":
    app.run(
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "5000")),
        debug=False,
    )
