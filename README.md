# Aram Trade Management System

Professional algorithmic trading research stack for strategy development, intraday backtesting, portfolio analytics, and Streamlit-based review.

## System Scope

- Strategy building under `strategies`
- Event-style intraday simulation in `core/backtester.py`
- Portfolio PnL and tearsheet metrics in `core/portfolio.py`
- Data ingestion and caching in `core/data_handler.py`
- Interactive analysis UI in `app.py`

## Ichimoku Strategy Package

- Canonical location: `strategies/ichimoku_strategy`
- Adapter used by the backtester: `strategies/ichimoku_strategy/strategy.py`
- Canonical signal layers:
	- `strategies/ichimoku_strategy/signals/layer1.py`
	- `strategies/ichimoku_strategy/signals/layer2.py`
	- `strategies/ichimoku_strategy/signals/layer3.py`
- Compatibility wrappers (`layer1_trend.py`, `layer2_entry.py`, `layer3_confirm.py`) are kept only to preserve existing import paths.

### Strategy Compliance Rules

- Strict no look-ahead: decisions use only information available at bar close.
- Signal outputs remain `-1/0/1` for integration with `core/backtester.py`.
- Session filtering and hard exit logic are handled in IST-aware utilities.
- Risk sizing and target generation are centralized in `execution/risk.py`.
- Data preprocessing enforces required OHLCV schema and intraday feature consistency.

## Quick Start

1. Install uv and Python 3.12.
2. Install dependencies:
	- `uv sync --group dev`
3. Run test and quality checks:
	- `uv run ruff check .`
	- `uv run mypy core strategies app.py main.py`
	- `uv run pytest`
4. Launch Streamlit:
	- `uv run streamlit run app.py`

## Backtest With Kaggle Minute CSV

Use your local file (for example `data/RELIANCE_minute.csv`) with timeframe resampling.

- Streamlit:
	- Select `Data Source = Local CSV (Kaggle/History)`
	- Set `CSV Path` to your file
	- Choose timeframe (`1m`, `5m`, `15m`, `30m`, `1h`, `1d`, etc.)
	- Tune risk and execution fields (SL, TP, TSL, slippage, commission, quantity)

- CLI:
	- Open `main.py`
	- Set `DATA_SOURCE = "csv"`
	- Set `CSV_PATH = "data/RELIANCE_minute.csv"`
	- Adjust `INTERVAL`, `DAYS_BACK`, and execution/risk constants
	- Run `uv run python main.py`

## Engineering Guardrails

- Signal contract must remain `-1/0/1`.
- Backtester output contract must remain `(tearsheet, metrics)`.
- PnL reconciliation must hold: final equity equals initial capital plus cumulative net PnL.
- No look-ahead bias in strategy or execution timing logic.

## Tooling Baseline

- Ruff lint + format
- Mypy static typing
- Pytest smoke and contract tests
- Pre-commit hooks
- GitHub Actions CI
- VS Code tasks and extension recommendations

For full setup details, see `SETUP_GUIDE.md` and `README.md`.

