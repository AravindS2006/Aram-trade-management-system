---
name: profile-backtest
description: "Profile backtest execution to identify CPU and memory bottlenecks, generate optimization recommendations."
argument-hint: "<strategy-file> [data-size: small|medium|large] [profile-type: cpu|memory|both]"
---

# Profile Backtest Prompt

Profile strategy execution to find performance bottlenecks and memory issues.

## Usage

```
/profile-backtest intraday_momentum_strategy.py --data-size large --profile-type both
```

## Profile Output

### CPU Profiling
```
Function                    Calls    Time(s)   % Time  Cumulative
─────────────────────────────────────────────────────────────────
indicator_calculation       1000     12.3      45%     12.3s
generate_signals            1000      8.2      30%     20.5s
portfolio_update            1000      4.1      15%     24.6s
trade_execution              500      2.4      9%      27.0s
```

### Memory Profiling
```
Line    Code                    Memory         Increment
─────────────────────────────────────────────────────────────
45      data = pd.read_csv()    45.2 MB        45.2 MB
78      indicators = calc()     89.5 MB        44.3 MB
92      results = backtest()   125.7 MB        36.2 MB
```

### Optimization Recommendations

```
Top Issues Found:
1. indicator_calculation: Loop over 1000 bars (45% time)
   Recommendation: Vectorize with DataFrame operations
   Estimated speedup: 50x

2. generate_signals: Type conversions in loop (30% time)
   Recommendation: Set dtypes early, avoid conversions
   Estimated speedup: 5x

3. portfolio_update: Repeated dictionary lookups (15% time)
   Recommendation: Use array indexing instead
   Estimated speedup: 2-3x

Expected total speedup: 100x+ with all optimizations
```

## Report Contents

- CPU profile (top 20 slowest functions)
- Memory usage timeline
- Bottleneck identification
- Optimization patterns suggested
- Risk assessment (refactoring impact)
- Before/after comparison (if optimizations applied)

## Common Scenarios

| Need | Command |
|------|---------|
| Find biggest CPU issue | `/profile-backtest my_strategy --profile-type cpu` |
| Check memory on large data | `/profile-backtest my_strategy --data-size large --profile-type memory` |
| Full analysis | `/profile-backtest my_strategy --data-size large --profile-type both` |
