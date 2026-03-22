# Backtest System

Core package for strategy research, intraday backtesting, and analytics UI.

## Architecture

- `core/strategy.py`: `BaseStrategy` contract
- `core/backtester.py`: `IntradayBacktester` execution engine
- `core/portfolio.py`: trade lifecycle and metric generation
- `core/data_handler.py`: data loading, filtering, caching
- `strategies/`: strategy implementations
- `app.py`: Streamlit app
- `main.py`: CLI-style pipeline
- `config/`: risk, backtest, execution, and logging templates

## Environment Setup

1. Install dependencies:
	- `uv sync --group dev`
2. Optional local env template:
	- copy `.env.example` to `.env`

## Developer Commands

- Lint: `uv run ruff check .`
- Format check: `uv run ruff format --check .`
- Type check: `uv run mypy core strategies app.py main.py`
- Tests: `uv run pytest`
- Run Streamlit: `uv run streamlit run app.py`
- Run pipeline: `uv run python main.py`
- Install git hooks: `uv run --directory .. pre-commit install`

## Discrepancy Prevention Checklist

Before merging strategy or execution changes:

1. Confirm signal values are limited to `-1/0/1`.
2. Confirm no look-ahead logic was introduced.
3. Confirm backtest runs without exceptions on sample data.
4. Confirm tearsheet includes `Net PnL` and `Equity` columns.
5. Confirm metric keys used by UI still exist.

## CI

GitHub Actions workflow runs lint, type-check, and tests on push/PR.
