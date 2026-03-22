---
name: data-analysis
description: "Use when: exploring OHLCV/trade datasets, validating data quality, producing strategy performance reports, or comparing backtest outputs. Keywords: EDA, anomalies, drawdown, return distribution, data integrity."
---

# Data Analysis Skill

Repository-focused workflow for robust market and backtest data analysis.

## When to Use

- EDA on files under `backtest_system/data/` or external CSV inputs
- Trade/tearsheet quality checks before trusting metrics
- Pattern analysis for volatility, trend, and session behavior
- Comparing strategy runs across parameter sets
- Building concise markdown reports for decisions

## Workflow

### 1. Load And Profile

#### Load & Inspect Data
```python
from core.data_handler import DataHandler
handler = DataHandler(data_dir='backtest_system/data')
data = handler.load_csv('backtest_system/data/RELIANCE_trades.csv')

# Baseline profile
print(data.shape)
print(data.columns)
print(data.head())
print(data.describe())
print(data.isnull().sum())
```

#### Key Validations
- Required columns exist: `Open`, `High`, `Low`, `Close`, `Volume`
- Index/timestamp is monotonic increasing
- No duplicate timestamps in active analysis window
- No non-positive prices in OHLC
- Volume is non-negative and distribution is plausible

### 2. Integrity Checks

Use these checks before advanced conclusions:

```python
ohlc_ok = (data['High'] >= data[['Open', 'Close']].max(axis=1)).all() and \
          (data['Low'] <= data[['Open', 'Close']].min(axis=1)).all()
is_sorted = data.index.is_monotonic_increasing
dupes = data.index.duplicated().sum()
```

### 3. Pattern Identification

#### Time Series Analysis
- Volatility trends (rolling std dev)
- Return distribution (daily % changes)
- Session patterns (time-of-day, day-of-week effects)
- Correlation with market events

#### Trade Analysis
- Win rate and profit factor
- Average winner vs loser
- Risk-reward ratios
- Drawdown depth and duration

### 4. Report Generation

Create comprehensive reports:
```
backtest_report.md
├── Summary Stats
│   ├── Total Return
│   ├── Sharpe Ratio
│   ├── Max Drawdown
│   └── Win Rate
├── Charts
│   ├── Portfolio Value Over Time
│   ├── Drawdown Curve
│   ├── Monthly Returns Heatmap
│   └── Return Distribution
├── Trade Analysis
│   ├── Win/Loss Trades
│   ├── Largest Wins/Losses
│   └── Duration Analysis
└── Risk Metrics
    ├── Value at Risk (VaR)
    ├── Conditional VaR
    └── Volatility Analysis
```

### 5. Visualization

Common plots:
- **Equity Curve**: Portfolio value over time
- **Drawdown Chart**: Peak-to-trough declines
- **Session Heatmap**: intraday return or volume concentration
- **Return Distribution**: Histogram of daily returns
- **Win/Loss Scatter**: Trade outcomes vs entry price

## Data Integrity Checks

Always validate:
1. No missing values in critical columns (`Open`, `High`, `Low`, `Close`).
2. `High >= max(Open, Close)` and `Low <= min(Open, Close)`.
3. Timestamps are unique and sorted.
4. Volume has no impossible values.
5. Extreme returns are explained or flagged.

## Deliverable Quality Bar

- Show assumptions and caveats explicitly.
- Separate observed facts from hypotheses.
- Include numeric evidence for every major claim.
