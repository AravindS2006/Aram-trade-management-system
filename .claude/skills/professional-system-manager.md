# Skill: Professional System Manager and Backtester - Aram-TMS

## Purpose
Use this skill when managing Aram-TMS as an institutional trading operations owner.
This skill unifies backtesting, data, risk, execution audit, and artifact governance.

## Mandatory Inputs
1. Trading mode: Backtest | Forward Test | Live Trading
2. Symbol scope: single symbol for deterministic validation
3. Timeframe: 1m | 5m | 15m | 30m | 1h | 1d | 1wk | 1mo
4. Date window: start and end date
5. Data source: yfinance | csv | auto
6. Strategy and parameters

## Mandatory Artifacts Per Run
1. Summary JSON with full run metadata and metrics
2. Equity curve parquet
3. Trade log parquet and trade log csv
4. Diagnostics payload: bars loaded, warmup requirement, signal counts, source
5. Audit log rows for all order intents and risk rejections (forward/live)

## Required Execution Parameters
1. Strategy parameters and warmup period
2. Capital and cost model assumptions
3. Timeframe and benchmark symbol
4. Risk controls: position caps, drawdown, stop-loss, rate limits
5. Environment identity: sandbox vs live

## Data Validation Workflow
1. Confirm symbol resolution and file/path presence.
2. Validate OHLCV columns and numeric conversion.
3. Validate date-range overlap before execution.
4. For intraday yfinance, ensure the requested window is provider-compatible.
5. If no rows remain after filtering, stop with explicit diagnostics.

## Trade Audit Workflow
1. Log all order intents, blocked orders, placements, and close requests.
2. Include: session_id, mode, strategy, symbol, side, quantity, price, order_value.
3. Include risk metadata: stop_loss, take_profit, risk_reasons, portfolio_value.
4. Include runtime metadata: timeframe, data_source, order_id, timestamp.
5. Store under logs/trades/session_day.csv.

## Backtest Professional Checklist
1. Single-symbol deterministic run completes without exceptions.
2. Signals are generated and warmup sufficiency is reported.
3. Metrics are cost-adjusted and benchmarked against NIFTY 50.
4. Output artifacts are persisted and machine-readable.
5. Dashboard displays actionable no-data diagnostics when load fails.

## Failure Handling Policy
1. Never emit generic no-data errors without source diagnostics.
2. Never silently ignore risk failures.
3. Never run live execution without explicit confirmation and credentials.
4. Always record rejected orders with reasons.

## Operational Commands
1. Backtest CLI:
python scripts/run_backtest.py --strategy MomentumStrategy --engine vectorbt --data-source csv --timeframe 1d --start 2024-01-01 --end 2024-12-31 --symbols RELIANCE

2. Forward test CLI:
python scripts/run_forward_test.py --strategy MomentumStrategy --symbols RELIANCE --data-interval 5m

3. Dashboard:
streamlit run src/dashboard/app.py

## Definition of Done
1. Trade logs are complete and schema-stable.
2. Backtest no-data states are diagnosable in one screen.
3. Required run parameters are persisted in artifacts.
4. Mode-specific behavior remains isolated and safe.
