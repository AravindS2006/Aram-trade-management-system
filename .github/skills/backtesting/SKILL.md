---
name: backtesting
description: "Use when: building, debugging, validating, or tuning strategies and backtests in repository root. Keywords: strategy signals, IntradayBacktester, Portfolio PnL, tearsheet metrics, look-ahead bias."
---

# Backtesting Skill

Production workflow for strategy and backtest tasks in this repository.

## When to Use

- Creating or editing strategy files in `strategies/`
- Debugging `IntradayBacktester` execution behavior
- Validating `Portfolio` PnL and tearsheet metrics
- Diagnosing no-trade / overtrade / unstable-result scenarios
- Tuning risk and stop parameters for controlled experiments

## Workflow

### 1. Confirm Runtime Contract

- Strategy base: `BaseStrategy` (`core/strategy.py`)
- Backtest runner: `IntradayBacktester` (`core/backtester.py`)
- Portfolio accounting: `Portfolio` (`core/portfolio.py`)
- Required signal output: `self.signals['signal']` with values `-1/0/1`

### 2. Strategy Development

#### Create a New Strategy
```python
from core.strategy import BaseStrategy

class MyStrategy(BaseStrategy):
    def generate_indicators(self):
        # Compute and store indicators in self.data
        self.data['EMA_20'] = self.data['Close'].ewm(span=20, adjust=False).mean()

    def generate_signals(self):
        buy = self.data['Close'] > self.data['EMA_20']
        sell = self.data['Close'] < self.data['EMA_20']
        self.signals.loc[buy, 'signal'] = 1
        self.signals.loc[sell, 'signal'] = -1
```

#### Strategy Rules
- Maintain integer signals only (`-1`, `0`, `1`).
- Keep logic vectorized where practical.
- Avoid look-ahead bias from future bars.
- Keep warmup NaNs from generating accidental signals.

### 3. Backtest Execution

Use the backtest runner:
```python
from core.backtester import IntradayBacktester
strategy = MyStrategy()
data_with_signals = strategy.get_data_with_signals()
backtester = IntradayBacktester(data_with_signals, initial_capital=100000)
tearsheet, metrics = backtester.run()
```

Check results:
- `tearsheet`: closed trade ledger and equity progression
- `metrics`: final performance dictionary for UI/CLI reporting

### 4. Validation And Analysis

Always validate:
- Signal frequency and side balance are plausible
- Trade open/close tags and timestamps are coherent
- `Final Equity` reconciles with cumulative `Net PnL`
- Drawdown and return metrics are numerically sane

### 5. Common Issues And Fixes

| Issue | Fix |
|-------|-----|
| No trades | Validate signal column values and one-bar execution shift impact |
| Unexpected entry/exit price | Recheck slippage direction and OHLC field used for execution |
| PnL mismatch | Reconcile tearsheet `Net PnL` sum with `Final Equity - Initial Capital` |
| Unrealistic metrics | Validate timestamp order, data quality, and transaction cost assumptions |

## Execution Checklist

After making strategy/backtest changes:

1. Run one short backtest using known symbol/date range.
2. Verify no exceptions and non-empty expected outputs.
3. Verify metric keys consumed by `app.py` still exist.
4. Verify behavior is deterministic for repeated runs with same input.

## Output Style

- Provide root-cause-first analysis.
- Include concrete file/function references.
- Report what was validated, not just what was changed.

