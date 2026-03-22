# Aram Trade Management System

Professional algorithmic trading research stack for strategy development, intraday backtesting, portfolio analytics, and Streamlit-based review.

## System Scope

- Strategy building under `backtest_system/strategies`
- Event-style intraday simulation in `backtest_system/core/backtester.py`
- Portfolio PnL and tearsheet metrics in `backtest_system/core/portfolio.py`
- Data ingestion and caching in `backtest_system/core/data_handler.py`
- Interactive analysis UI in `backtest_system/app.py`

## Quick Start

1. Install uv and Python 3.12.
2. Install dependencies:
	- `uv sync --directory backtest_system --group dev`
3. Run test and quality checks:
	- `uv run --directory backtest_system ruff check .`
	- `uv run --directory backtest_system mypy core strategies app.py main.py`
	- `uv run --directory backtest_system pytest`
4. Launch Streamlit:
	- `uv run --directory backtest_system streamlit run app.py`

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

For full setup details, see `SETUP_GUIDE.md` and `backtest_system/README.md`.
