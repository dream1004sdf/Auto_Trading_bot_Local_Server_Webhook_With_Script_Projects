# Resume and interview reference

## Project

**Python Trading Automation & Backend Development** — Personal Project

**Initial development:** 2024–2025  
**Portfolio engineering cleanup:** October 2026

**Technologies:** Python, Flask, REST APIs, JSON Webhooks, Pandas, InfluxDB 1.x (optional), TradingView Pine Script, pytest, GitHub Actions.

## ATS-friendly bullet options

- Developed a Python/Flask backend to receive, authenticate and validate TradingView webhook signals using structured JSON and REST endpoints.
- Implemented technical-indicator calculations in Pandas, including RSI, Bollinger Bands and ATR, with optional InfluxDB time-series integration.
- Refactored a trading automation prototype into a safe local demonstration with simulated order requests, error handling, automated unit tests and GitHub Actions CI.

**Use only if explaining the older prototype as experimental:** Investigated Coinbase REST endpoints for exchange data and order workflows; current public demonstration does not provide verified live order execution.

## How to discuss the project in an interview

**Goal:** Connect external alerts to a Python backend and explore systematic technical indicator processing.

**Architecture:** TradingView JSON alert → Flask validation → optional InfluxDB storage → separately supplied OHLC series → Pandas indicator calculation.

**Engineering decisions:** Stronger validation, separation of historical research from verified API functionality, no real-trade endpoints in a public code sample, mocked tests and CI.

**What I learned:** The distinction between an API proof of concept and production-ready integration, safer handling of secrets, HTTP error boundaries and repeatable testing.

**Evidence:** See `Server.py`, `tests/test_server.py`, `.github/workflows/tests.yml`, and `docs/TESTING.md`.

## Do not claim without independent evidence

- Successful live Coinbase orders or end-to-end brokerage authentication
- A production-deployed service or tested real-market execution
- Guaranteed strategy profitability or audited backtesting
- Complete Supertrend calculations (current code returns ATR-based bands)
- Verified InfluxDB integration with a real external server
- A performance improvement percentage or signal accuracy not actually measured
