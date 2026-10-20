# Python Trading Automation — Backend Portfolio Project

A **demo-first Python/Flask backend** for receiving TradingView webhook signals, validating JSON, calculating technical indicators from historical OHLC data, and optionally recording events in InfluxDB 1.x. Five original Pine Script experiments are retained as examples of signal-generation research.

> **Portfolio demonstration, not a production trading system.** Live brokerage orders and wallet access are intentionally disabled. Earlier prototype work explored Coinbase REST integration, but this version does not claim functioning exchange authentication or live execution.

## What it demonstrates

- **HTTP backend:** Flask endpoints, JSON validation, configurable webhook token verification, structured API responses.
- **Data and indicators:** Pandas-based RSI, Bollinger Bands, ATR, and ATR-derived price bands (not a complete Supertrend trend-state calculation).
- **Optional data storage:** InfluxDB 1.x writes for validated webhooks; indicator refresh from the separately populated `trading_metrics` OHLC series.
- **Safe simulation:** `/trade` validates a proposed limit order and returns an illustrative result without placing an exchange order.
- **Quality and security:** pytest coverage, GitHub Actions, no credentials in source, loopback-only default, and opt-in storage.

## Stack

Python 3.11+, Flask, Pandas, NumPy, InfluxDB 1.x (optional), TradingView Pine Script v5/v6, pytest, GitHub Actions.

## API

| Method | Endpoint | Behavior |
| --- | --- | --- |
| GET | `/health` | Service status and demo configuration |
| POST | `/webhook` | Validates an alert; optionally persists filtered event fields |
| POST | `/trade` | **Simulates** a limit-order payload; does not submit an order |
| GET | `/wallet` | Deliberately disabled (HTTP 501) |
| GET | `/update_strategies` | Computes indicators from separately supplied InfluxDB OHLC data |

## Local quick start

```bash
python -m venv .venv
# Activate .venv using your platform's shell
python -m pip install -r requirements.txt
python Server.py
```

Open `http://127.0.0.1:5000/health`. On a separate terminal:

```bash
curl -X POST http://127.0.0.1:5000/webhook -H "Content-Type: application/json" -d '{"symbol":"BTC-USD","action":"buy"}'
curl -X POST http://127.0.0.1:5000/trade -H "Content-Type: application/json" -d '{"side":"buy","product_id":"BTC-USD","size":0.01,"price":50000}'
python -m pytest -q
```

Without InfluxDB, webhook events are accepted and validated **but not persisted**. The simulated trade endpoint never places an order. By default, the Flask server binds to `127.0.0.1`, not the public internet.

## Configuration

Copy `.env.example` as a reference, but **set the environment variables in your shell**: the program does not auto-load a `.env` file. Set `WEBHOOK_TOKEN` to a long random secret before using a remotely accessible webhook; it may be sent in the `X-Webhook-Token` header or JSON `token` property. Avoid exposing the development server to the internet. `INFLUXDB_ENABLED=false` by default.

Optional InfluxDB 1.x configuration: `INFLUXDB_ENABLED=true`, `INFLUXDB_HOST`, `INFLUXDB_PORT`, `INFLUXDB_DATABASE`. The `trading_metrics` measurement must be populated separately with `time`, `high`, `low`, and `close` records; webhooks do not automatically build an OHLC series. The optional DB integration and existing Pine Script studies have not been end-to-end validated in this portfolio cleanup.

## Historical Pine Script experiments

The repository also contains five exploratory TradingView scripts for strategy ideas such as EMA crossover, RSI, Bollinger Bands, reversal detection, and Supertrend variations. **Experimental scripts are not presented as a verified profitable system.** Some are historical work with different exchange assumptions and require independent review before use.

## Architecture

```text
TradingView/Pine strategy → JSON webhook → Flask validation
                                      ├→ demo response (default)
                                      └→ InfluxDB 1.x (optional)
                                            └→ OHLC series → Pandas indicators
Manual order proposal → Flask validation → simulated order response
```

## Scope and limitations

- Coinbase authentication and live trading are **not implemented in this public portfolio version**.
- Core indicators use rolling moving averages; the ATR-derived "Supertrend" values represent **bands only**, not a full signal-generating trend algorithm.
- This project focuses on backend programming, API design, validation, basic analytics, and software-development hygiene—not trading results or investment performance.
- No production reliability, security audit, or exchange certification is claimed.

## Security

Never commit real credentials, webhook tokens, private account data, or trading history. If a secret was previously published, rotate/revoke it: removing it from the latest revision does not erase Git history.
