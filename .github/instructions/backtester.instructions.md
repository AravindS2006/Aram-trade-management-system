---
applyTo: "backtest_system/core/backtester.py"
description: "Use when: editing IntradayBacktester execution flow, signal timing, stop logic, slippage, or square-off behavior."
---

# Backtester Implementation Instructions

Use this guidance when changing `IntradayBacktester` in `backtest_system/core/backtester.py`.

## Canonical Behavior

- Input is `data_with_signals` with a `signal` column.
- Execution is intentionally delayed by one bar using `exec_signal = signal.shift(1)`.
- Entry executes using bar `Open` adjusted by slippage.
- Forced intraday exit occurs at or after `15:15`.
- Stop-loss / take-profit / trailing-stop logic evaluates within each bar.
- Trade open/close is delegated to `Portfolio.update_position(...)`.
- `run()` returns `portfolio.generate_tearsheet()`.

## Non-Negotiable Invariants

- Do not remove one-bar signal shift unless explicitly requested by user.
- Do not break long/short sign conventions:
  - long quantity `> 0`
  - short quantity `< 0`
- Any exit must flatten the active position quantity to zero.
- Backtester must remain deterministic for same input data and params.
- Slippage direction must remain side-aware:
  - long entry worse price (up)
  - long exit worse price (down)
  - short entry worse price (down)
  - short exit worse price (up)

## Change Safety Checklist

- Verify entry/exit tags remain meaningful (`LONG_ENTRY`, `SHORT_ENTRY`, `SL_HIT`, `TP_HIT`, `TIME_EXIT`).
- Verify risk sizing cannot produce zero quantity.
- Verify no branch leaves `position`/`current_qty` in an inconsistent state.
- Verify returned tearsheet and metrics schema remain unchanged.
- Verify edits preserve compatibility with `backtest_system/app.py` rendering path.

## Validation Steps

After modifying this file:

1. Run a short backtest and ensure no exceptions.
2. Confirm trades are generated when signals exist.
3. Confirm forced square-off closes open positions near session end.
4. Confirm `Total Trades` and `Final Equity` are present in metrics.
