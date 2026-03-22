---
applyTo: "backtest_system/core/portfolio.py"
description: "Use when: changing Portfolio state transitions, PnL accounting, trade close logic, or tearsheet metric generation."
---

# Portfolio Implementation Instructions

Use this file when editing `Portfolio` in `backtest_system/core/portfolio.py`.

## Canonical Responsibilities

- Track per-symbol signed position quantity in `self.positions`.
- Manage open trade metadata in `self.active_trades`.
- Close trades into `self.closed_trades` with full audit fields.
- Build equity history and tearsheet metrics via `generate_tearsheet()`.

## Critical Contracts

- `update_position(...)` is the single trade state transition entry point.
- A trade is considered opened when previous quantity is `0` and `qty != 0`.
- A trade is considered closed when resulting quantity becomes `0`.
- `calculate_intraday_costs(...)` must remain part of net PnL computation.
- `Net PnL = Gross PnL - total_charges` must hold for each closed trade.

## Reconciliation Rules

- `Final Equity = Initial Capital + sum(Net PnL)`.
- `Cumulative Net PnL` must be monotonic cumulative sum of per-trade `Net PnL`.
- `Equity` in tearsheet must equal `Initial Capital + Cumulative Net PnL`.
- Drawdown and run-up should be computed from tearsheet equity series only.

## Editing Guardrails

- Preserve existing tearsheet column names unless migration is explicitly requested.
- Do not remove audit columns (`Entry Time`, `Exit Time`, `Entry Price`, `Exit Price`, `Quantity`, `Net PnL`, tags, charges).
- Keep rounding behavior consistent where already applied.
- If adding metrics, avoid changing existing metric keys consumed by UI.

## Validation Checklist

After changes to this file:

1. Confirm a long trade close computes positive/negative net PnL correctly.
2. Confirm a short trade close computes positive/negative net PnL correctly.
3. Confirm empty closed trades returns `(None, {})` behavior unchanged.
4. Confirm `Total Trades`, `Final Equity`, and `Total Return %` are still produced.
