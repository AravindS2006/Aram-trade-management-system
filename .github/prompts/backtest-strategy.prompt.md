---
name: backtest-strategy
description: "Run a strategy through the backtesting pipeline in backtest_system and return tearsheet, key metrics, and execution diagnostics."
argument-hint: "<strategy-file> [data-file: backtest_system/data/RELIANCE_trades.csv] [initial-capital: 100000]"
---

# Backtest Strategy Prompt

Run a complete backtest workflow on a strategy, capturing results and generating insights.

## Usage

```
/backtest-strategy intraday_momentum_strategy.py --data-file backtest_system/data/RELIANCE_trades.csv --initial-capital 50000
```

## Workflow

1. **Validate Strategy**: Check file exists and inherits from `BaseStrategy`
2. **Load Data**: Read CSV, validate format and integrity
3. **Run Backtest**: Build `data_with_signals` and execute `IntradayBacktester`
4. **Calculate Metrics**: Use returned `metrics` and tearsheet reconciliation checks
5. **Generate Report**: 
   - Summary statistics table
   - Equity curve chart
   - Drawdown analysis
   - Trade distribution
   - Risk metrics
6. **Create Artifacts**: Optionally save report to `backtest_system/data/output/backtest_[strategy].md`

## Output Example

```
┌─────────────────────────────────────┐
│   BACKTEST RESULTS: my_strategy     │
├─────────────────────────────────────┤
│ Starting Capital:   $100,000        │
│ Ending Value:       $145,230        │
│ Total Return:       45.23%          │
│ Sharpe Ratio:       1.24            │
│ Max Drawdown:       -18.5%          │
│ Win Rate:           58%             │
│ Profit Factor:      1.89            │
│ # Trades:           124             │
└─────────────────────────────────────┘

[Equity Curve Chart]
[Drawdown Chart]
[Win/Loss Distribution]
```

## Common Parameters

| Scenario | Command |
|----------|---------|
| Quick test with minimal data | `/backtest-strategy test_strat --data-file data/sample.csv` |
| Production backtest | `/backtest-strategy prod_strat --starting-capital 1000000` |
| Compare multiple strategies | `/backtest-strategy strat1 && backtest-strategy strat2` |
