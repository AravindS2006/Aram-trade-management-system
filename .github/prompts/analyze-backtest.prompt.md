---
name: analyze-backtest
description: "Perform deep analysis on backtest tearsheet/metrics outputs and provide actionable improvement recommendations."
argument-hint: "<tearsheet-file-or-dataframe> [report-type: detailed|summary] [format: md|html]"
---

# Analyze Backtest Prompt

Deep dive into backtest results with comprehensive analysis and actionable insights.

## Usage

```
/analyze-backtest data/output/backtest_intraday_momentum_strategy.csv --report-type detailed --output-format html
```

## Analysis Includes

### Performance Metrics
- **Returns**: Absolute, average daily, monthly
- **Risk**: Volatility, Sharpe ratio, Sortino ratio, max drawdown, VaR
- **Efficiency**: Return/risk ratio, calmar ratio, recovery factor
- **Consistency**: Win rate, profit factor, consecutive losses

### Trade Analysis
- **Win/Loss Distribution**: Histogram, statistics
- **Largest Wins/Losses**: Identifying outliers
- **Trade Duration**: Average time in position
- **Entry/Exit Quality**: Analysis of signal timing
- **Commission Impact**: Absolute and relative cost

### Regime Analysis
- **Volatility Regimes**: High vol vs low vol periods
- **Time Patterns**: Day-of-week, time-of-day effects
- **Drawdown Events**: When and why largest losses occurred

### Improvement Suggestions
- Parameter tweaks to try
- Risk management enhancements
- Cost reduction opportunities
- Position sizing improvements

## Report Structure

```
1. Executive Summary
   - Key metrics at a glance
   - Strategy strengths and weaknesses
   
2. Performance Analysis
   - Returns breakdown
   - Risk metrics
   - Efficiency ratios
   
3. Trade Analysis
   - Win/loss statistics
   - Largest wins/losses
   - Trade duration patterns
   
4. Risk Analysis
   - Drawdown events
   - Volatility analysis
   - Correlation patterns
   
5. Recommendations
   - Parameter optimization
   - Risk improvements
   - Cost reduction
```

## Common Analyses

| Goal | Command |
|------|---------|
| Quick summary | `/analyze-backtest results.json --report-type summary` |
| HTML report for client | `/analyze-backtest results.json --output-format html` |
| Identify biggest losses | `/analyze-backtest results.json --report-type detailed` |
| Compare two strategies | `/analyze-backtest strat1.csv vs strat2.csv` |

