# Aram Trade Management System - Workspace Instructions

These instructions apply to all coding tasks in this repository and define the canonical architecture, contracts, and quality bar.

## Source Of Truth Paths

- Main package root: repository root
- Backtester engine: `core/backtester.py`
- Portfolio engine: `core/portfolio.py`
- Strategy base class: `core/strategy.py`
- Data loading: `core/data_handler.py`
- Indicators: `core/indicators.py`
- Strategy implementations: `strategies/*.py`
- Streamlit UI: `app.py`

## Canonical Runtime Contracts

- Strategy classes must inherit `BaseStrategy` from `core/strategy.py`.
- Strategy interface uses:
	- `generate_indicators(self)`
	- `generate_signals(self)`
	- `get_data_with_signals(self)`
- Signal column contract: `signal` with values `-1`, `0`, `1`.
- Backtest runner class is `IntradayBacktester` and `run()` returns `(tearsheet_df, metrics_dict)`.
- Portfolio class is `Portfolio`; trade lifecycle and metric construction are in `update_position()` and `generate_tearsheet()`.

## Engineering Standards

- Preserve existing public method names unless the task explicitly requests API change.
- Prefer minimal, targeted edits over broad refactors.
- Keep math-sensitive logic deterministic and auditable.
- Add type hints and concise docstrings to new/changed functions.
- Never introduce look-ahead bias in strategy or execution logic.

## Data And Backtest Safety Rules

- Always validate OHLCV shape and required columns before strategy execution.
- Ensure timestamp ordering is ascending before simulation.
- Preserve these invariants when editing portfolio/backtester logic:
	- Closed-trade `Net PnL` must reconcile with `Final Equity - Initial Capital`.
	- Equity curve must remain traceable to realized PnL sequence.
	- Position sign and quantity semantics must stay consistent (long positive, short negative).
- If changing costs/slippage behavior, verify downstream metrics still reconcile.

## Performance Rules

- Prefer vectorized pandas/numpy operations for indicator generation.
- Avoid repeated recomputation inside loops when values can be precomputed as columns.
- Profile before optimization if the user asks for speed improvements.

## Streamlit Rules

- Keep layout stable on both desktop and mobile widths.
- Isolate expensive operations behind explicit user action (button/form submit).
- Protect UI rendering from dtype/serialization crashes by formatting display DataFrames safely.

## Skills And File Instructions

- Use `.github/instructions/*.instructions.md` for file-scoped guardrails.
- Use `.github/skills/*/SKILL.md` for multi-step task workflows.
- Keep guidance aligned to actual code paths under repository root.

