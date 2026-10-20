"""Flask portfolio demo tests — no brokerage or database required."""
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
    assert client.post("/webhook", json={"symbol":"BTC-USD"}).status_code == 401

def test_webhook_accepts_token(client):
    response = client.post("/webhook", json={"symbol":"BTC-USD","token":"example-secret"})
    assert response.status_code == 200
    assert response.json["stored"] is False

def test_webhook_rejects_bad_json(client):
    assert client.post("/webhook", data="invalid", content_type="application/json").status_code == 400

def test_credentials_are_not_persisted():
    assert Server.safe_fields({"symbol":"BTC-USD","token":"secret","api_key":"secret"}) == {"symbol":"BTC-USD"}

def test_trade_is_simulated(client):
    response = client.post("/trade", json={"side":"buy","product_id":"BTC-USD","size":0.01,"price":50000})
    assert response.status_code == 200
    assert response.json["live_order_submitted"] is False

def test_invalid_trade(client):
    assert client.post("/trade", json={"side":"buy","size":1,"price":-1}).status_code == 400

def test_wallet_disabled(client):
    assert client.get("/wallet").status_code == 501

def test_price_indicators():
    frame = pd.DataFrame({"high":[i+101 for i in range(40)],"low":[i+99 for i in range(40)],"close":[i+100 for i in range(40)]})
    values = Server.calculate_indicators(frame)
    assert values["RSI"] == 100.0
    assert values["ATR"] is not None
    assert values["Supertrend_Band_Upper"] is not None

def test_short_history():
    frame = pd.DataFrame({"high":[2],"low":[1],"close":[1.5]})
    assert Server.calculate_indicators(frame)["ATR"] is None
