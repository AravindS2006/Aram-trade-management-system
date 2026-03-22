# Backtest Validation Checklist

Before considering a backtest result reliable, verify these items:

## Data Validation

- [ ] **N of records**: Expected number of candles?
- [ ] **Time range**: Covers intended period?
- [ ] **Missing data**: Any gaps or duplicates in timestamps?
- [ ] **Price validity**: All OHLC > 0?
- [ ] **OHLC consistency**: High ≥ max(Open,Close), Low ≤ min(Open,Close)?
- [ ] **Volume**: All volume > 0 and realistic for exchange?
- [ ] **Chronological order**: Timestamps strictly ascending?

## Strategy Validation

- [ ] **Signal generation**: Produces values only in {-1, 0, 1}?
- [ ] **Edge case handling**: Works with <lookback bars?
- [ ] **No look-ahead bias**: Uses only data available at bar time?
- [ ] **Reproducible**: Same results on second run?
- [ ] **Documented parameters**: All configurable values documented?

## Backtest Configuration

- [ ] **Starting capital**: Realistic for your use case?
- [ ] **Commission/slippage**: Accounted for?
- [ ] **Position sizing**: Consistent and realistic?
- [ ] **Margin requirements**: Enforced if using leverage?
- [ ] **Execution timing**: Entry/exit at correct price?

## Results Sanity Check

- [ ] **Return magnitude**: Between -100% and +1000% (reasonable bounds)?
- [ ] **Sharpe ratio**: Between -2 and +5 (warning if >5)?
- [ ] **Drawdown**: Ever exceeds portfolio size? (red flag)
- [ ] **Trade count**: >5 trades? (<5 suggests insufficient opportunities)
- [ ] **Win rate**: Between 20% and 80%? (outside = suspect)
- [ ] **Positive correlation**: Returns and capital growth correlated?

## Metric Verification (Manual Calculation)

For a 5-trade backtest:

```
Trade 1: Entry 100 → Exit 105 → PnL: +5
Trade 2: Entry 105 → Exit 103 → PnL: -2
Trade 3: Entry 103 → Exit 110 → PnL: +7
Trade 4: Entry 110 → Exit 108 → PnL: -2
Trade 5: Entry 108 → Exit 112 → PnL: +4
────────────────────────────────
Total: +12 (gross)
Minus commissions (5 trades × $10): -50
Net P&L: -38
Return: -38 / 10000 = -0.38%

Verify: Backtest result matches hand calculation? ✓
```

## Backtester Consistency

- [ ] **Portfolio value updated**: After every trade?
- [ ] **Cash balance correct**: Cash = starting - positions_cost - commissions?
- [ ] **NAV invariant**: NAV = cash + position_value always?
- [ ] **Returns traceable**: Cumulative = (final_NAV - start_capital) / start_capital?
- [ ] **Trade log**: Every trade recorded with entry/exit prices?

## Final Signs of Reliable Backtest

✅ **All checkboxes passed**
✅ **Manual calculations match results**
✅ **Results visually reasonable** (smooth equity curve, no spikes)
✅ **Runnable code**: No errors, warnings, or assumptions
✅ **Documented**: Strategy logic clear, parameters justified

🚩 **Red Flags**

- Too-good-to-be-true results (Sharpe >5, returns >100%)
- Inconsistent portfolio value (negative or spikes)
- Missing trades or execution gaps
- Inconsistent data (jumps, duplicates, gaps)
- Unexplained changes between runs

## If Results Fail Validation

1. **Review data**: Use `/explore-data` to deep-dive
2. **Trace execution**: Use `/debug-portfolio` bar-by-bar
3. **Check logic**: Print intermediate values in `generate_signals()`
4. **Verify math**: Manually calculate 5-10 trades
5. **Iterate**: Fix one issue at a time, re-test

