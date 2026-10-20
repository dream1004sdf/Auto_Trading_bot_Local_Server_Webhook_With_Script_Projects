"""Tests for demo HTTP endpoints and basic technical-indicator math.

No live brokerage calls or an InfluxDB server are required.
"""
import json

import pandas as pd
import pytest

import Server


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("INFLUXDB_ENABLED", "false")
    monkeypatch.setenv("WEBHOOK_TOKEN", "example-secret")
    Server.app.config.update(TESTING=True)
    return Server.app.test_client()


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json["demo_mode"] is True


def test_webhook_rejects_missing_token(client):
    assert client.post("/webhook", json={"symbol": "BTC-USD"}).status_code == 401


def test_webhook_accepts_token(client):
    response = client.post("/webhook", json={"symbol": "BTC-USD", "token": "example-secret"})
    assert response.status_code == 200
    assert response.json["stored"] is False


def test_webhook_accepts_header_token(client):
    response = client.post("/webhook", json={"symbol": "BTC-USD"}, headers={"X-Webhook-Token": "example-secret"})
    assert response.status_code == 200


def test_webhook_rejects_invalid_token(client):
    response = client.post("/webhook", json={"symbol": "BTC-USD", "token": "wrong-secret"})
    assert response.status_code == 401


def test_webhook_rejects_bad_json(client):
    response = client.post("/webhook", data="invalid", content_type="application/json")
    assert response.status_code == 400


def test_webhook_rejects_list_json(client):
    response = client.post("/webhook", json=["not", "an", "object"])
    assert response.status_code == 400


def test_credentials_are_not_persisted():
    assert Server.safe_fields({"symbol": "BTC-USD", "token": "secret", "api_key": "secret"}) == {"symbol": "BTC-USD"}


def test_nested_payload_is_serialized():
    result = Server.safe_fields({"symbol": "SOL-USD", "indicator": {"rsi": 60}})
    assert json.loads(result["indicator"]) == {"rsi": 60}


def test_trade_is_simulated(client):
    response = client.post("/trade", json={"side": "buy", "product_id": "BTC-USD", "size": 0.01, "price": 50000})
    assert response.status_code == 200
    assert response.json["live_order_submitted"] is False


def test_invalid_trade(client):
    assert client.post("/trade", json={"side": "buy", "size": 1, "price": -1}).status_code == 400


def test_nonfinite_trade_price(client):
    assert client.post("/trade", json={"side": "buy", "size": 1, "price": "nan"}).status_code == 400


def test_wallet_disabled(client):
    assert client.get("/wallet").status_code == 501


def test_price_indicators():
    frame = pd.DataFrame({
        "high": [i + 101 for i in range(40)],
        "low": [i + 99 for i in range(40)],
        "close": [i + 100 for i in range(40)],
    })
    values = Server.calculate_indicators(frame)
    assert values["RSI"] == 100.0
    assert values["ATR"] is not None
    assert values["Supertrend_Band_Upper"] is not None


def test_short_history():
    frame = pd.DataFrame({"high": [2], "low": [1], "close": [1.5]})
    assert Server.calculate_indicators(frame)["ATR"] is None


def test_flat_price_rsi():
    frame = pd.DataFrame({"high": [101] * 20, "low": [99] * 20, "close": [100] * 20})
    assert Server.calculate_indicators(frame)["RSI"] == 50.0


def test_invalid_indicator_window():
    frame = pd.DataFrame({"high": [3], "low": [1], "close": [2]})
    with pytest.raises(ValueError, match="Invalid period"):
        Server.calculate_indicators(frame, {"RSI_Length": 0})


def test_influxdb_write_path_uses_sanitized_payload(client, monkeypatch):
    recorded = []

    class FakeInfluxDB:
        def write_points(self, points):
            recorded.extend(points)

    monkeypatch.setenv("INFLUXDB_ENABLED", "true")
    monkeypatch.setattr(Server, "get_influx_client", lambda: FakeInfluxDB())
    monkeypatch.setattr(Server, "query_indicators", lambda _client: {"RSI": 55.0})
    response = client.post("/webhook", json={
        "symbol": "BTC-USD", "token": "example-secret", "api_key": "not-an-api-key"
    })
    assert response.status_code == 200
    assert response.json["stored"] is True
    assert response.json["indicators"]["RSI"] == 55.0
    assert recorded[0]["fields"] == {"symbol": "BTC-USD"}


def test_influxdb_failure_returns_503(client, monkeypatch):
    monkeypatch.setenv("INFLUXDB_ENABLED", "true")

    def unavailable():
        raise ConnectionError("DB connection down")

    monkeypatch.setattr(Server, "get_influx_client", unavailable)
    response = client.post("/webhook", json={"symbol": "BTC-USD", "token": "example-secret"})
    assert response.status_code == 503
    assert "connection" not in response.get_data(as_text=True).lower()


def test_update_strategies_requires_database(client):
    assert client.get("/update_strategies").status_code == 503
