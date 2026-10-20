# Code walkthrough and architecture decisions

This document explains the actual public demo implementation for code reviewers. It is **not** a claim that the system safely executes real trades.

## Repository map

| File | Responsibility |
| --- | --- |
| `Server.py` | Flask API, authentication checks, payload validation, optional InfluxDB operations and technical indicators |
| `tests/test_server.py` | Automated endpoint, validation, calculation and mocked persistence tests |
| `requirements.txt` | Python application and test dependencies |
| `.github/workflows/tests.yml` | GitHub Actions CI across operating systems and Python versions |
| `.env.example` | Configuration variable reference (not automatically loaded) |
| `.gitignore` | Excludes credentials, local virtual environments and local generated files from future commits |
| `*.pinescript` | Five historical TradingView signal-generation experiments |

## HTTP request lifecycle

1. TradingView or a test client sends JSON to `POST /webhook`.
2. `request.get_json(silent=True)` validates that the body is nonempty JSON object.
3. `verify_webhook_token` compares the optional `X-Webhook-Token` header/JSON secret with `WEBHOOK_TOKEN` using `hmac.compare_digest` when configured. With no configured token, localhost demos are accepted.
4. `safe_fields` excludes credential-like keys and sanitizes values for the optional database write. It does not attempt to validate the business meaning of arbitrary signals.
5. With `INFLUXDB_ENABLED=false` (default), the handler responds with `stored: false`, clearly indicating it did not persist anything.
6. With InfluxDB enabled, `get_influx_client` establishes a client for an InfluxDB **1.x** instance and writes a point to `webhook_data`.
7. `query_indicators` reads a **separately populated** `trading_metrics` OHLC series; `calculate_indicators` computes current indicator values in Pandas.
8. Errors in the optional data-service path are logged; the HTTP client receives a generic 503 rather than internal exception details.

## Technical-indicator implementation

- `calculate_rsi`: classic RSI based on rolling average gains and losses. Handles increasing and flat windows with 100 or 50.
- `calculate_bollinger_bands`: rolling mean plus/minus rolling standard deviation times a multiplier.
- `calculate_atr`: per-candle maximum of three true-range candidates, then rolling mean.
- `calculate_supertrend_bands`: ATR-adjusted bands around the candle midpoint. This is **not** full Supertrend trend direction / regime switching.
- `calculate_indicators`: validates parameter ranges, orders time series if a time column exists, cleans OHLC fields, returns latest finite values or null for insufficient history.

Data-source note: the alert-ingestion and OHLC measurement are separate. Sending a webhook does not automatically produce price candles.

## Simulated orders, not real execution

`POST /trade` checks `side`, `product_id`, `size` and `price` and returns a JSON preview with `live_order_submitted: false`. It **does not** import a brokerage SDK, sign API requests or send a network request to an exchange. `GET /wallet` returns HTTP 501 to make that distinction explicit.

## Engineering considerations

- **Separation of concerns:** input validation, indicator mathematics, optional DB operations and HTTP response handling are distinct functions, although still in one Flask module.
- **Safe defaults:** localhost binding, disabled DB, no live trade path.
- **Testability:** mocked database tests exercise success and failure behavior without personal brokerage credentials or an external database.
- **Limitations:** Flask development server, optional token, no per-user identity/rate limiting, no full integration tests, and legacy `GET /update_strategies` changes server state.

## How to review or extend

1. Run `python -m pytest -q`.
2. Run `python Server.py`; inspect `/health`, then test `/webhook` and `/trade` on localhost.
3. For real market-data integration, add independent InfluxDB fixtures/tests before claiming verified persistence.
4. For full Supertrend, implement state transitions and add known-reference test cases.
5. Before any production use, redesign authentication, deployment security, idempotency, rate limiting, API integration and observability.

Historical Pine Script studies may require revision before compilation or use; their presence is evidence of experimentation, not evidence of live profitability.
