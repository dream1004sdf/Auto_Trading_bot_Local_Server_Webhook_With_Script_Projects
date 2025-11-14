# TradingView → Flask → Coinbase Automation Server

This project exposes a Flask server that:

- Receives webhook alerts from TradingView
- Logs data into InfluxDB
- Calculates indicators (RSI, Bollinger Bands, ATR, Supertrend)
- Optionally sends limit orders to Coinbase (demo mode by default)

## Features

- `/webhook` – receives TradingView alerts (with optional secret token)
- `/wallet` – fetches account information from Coinbase (requires API key)
- `/trade` – places limit orders (disabled when `DEMO_MODE=true`)
- `/update_strategies` – recalculates indicators from InfluxDB data

## Tech Stack

- Python, Flask
- InfluxDB
- Pandas, NumPy
- REST APIs (Coinbase)
- TradingView Webhooks

## Environment Variables

See `.env.example`:

- `INFLUXDB_HOST`, `INFLUXDB_PORT`, `INFLUXDB_DATABASE`
- `COINBASE_API_KEY`, `COINBASE_API_SECRET`
- `WEBHOOK_TOKEN`
- `DEMO_MODE`

## Run locally

```bash
pip install -r requirements.txt
export FLASK_APP=server.py
python server.py
