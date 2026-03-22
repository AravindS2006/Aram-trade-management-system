---
applyTo: "backtest_system/strategies/*.py"
description: "Use when: implementing or modifying strategy files that inherit BaseStrategy and emit -1/0/1 signals."
---

# Strategy Development Instructions

Apply these rules to files in `backtest_system/strategies/`.

## Canonical Strategy Contract

- Inherit from `BaseStrategy` from `backtest_system/core/strategy.py`.
- Use `self.data` and `self.signals` initialized by `BaseStrategy`.
- Implement exactly:
  - `generate_indicators(self)`
  - `generate_signals(self)`
- `self.signals['signal']` must contain only `-1`, `0`, `1`.
- Return combined frame through inherited `get_data_with_signals()`.

## Data Assumptions

- Input DataFrame should contain `Open`, `High`, `Low`, `Close`, `Volume`.
- Do not mutate caller-owned DataFrame outside the strategy copy.
- Handle warmup periods (`rolling`, EMA, RSI) without emitting invalid signals.

## Signal Rules

- Use vectorized boolean masks; avoid per-row Python loops unless strictly required.
- Keep entry and exit conditions explicit and readable.
- Avoid look-ahead bias; use shifted values only when intentionally needed.

## Reliability Checklist

After editing strategy logic:

1. Confirm signal column exists and contains only `-1/0/1`.
2. Confirm output index aligns with input index.
3. Confirm strategy runs with small and large datasets.
4. Confirm no runtime errors when indicators contain NaN at start of series.

## Avoid

- Introducing global mutable state.
- Hardcoding symbol-specific values without parameterization.
- Creating strategy APIs that diverge from `BaseStrategy` contract.
