---
name: performance-optimization
description: "Use when: backtests are slow, indicator computations lag, or memory usage is high. Keywords: profile, benchmark, vectorize, cache, bottleneck, optimization regression check."
---

# Performance Optimization Skill

Systematic process for safe speed and memory improvements in this repository.

## When to Use

- Backtests are materially slower than expected for dataset size
- Streamlit interactions feel blocked by compute paths
- Indicator generation is dominant runtime
- Memory spikes occur with larger historical windows

## Workflow

### 1. Profile & Identify Bottlenecks

#### CPU Profiling
```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Run target operation
tearsheet, metrics = backtester.run()

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)  # Top 20 functions
```

#### Memory Profiling
```python
from memory_profiler import profile

@profile
def load_data():
    # Your code here
    pass
```

#### Measure Execution Time
```python
import time
start = time.perf_counter()
# Operation
elapsed = time.perf_counter() - start
print(f"Took {elapsed:.3f}s")
```

### 2. Common Bottlenecks & Fixes

| Bottleneck | Symptoms | Fix |
|------------|----------|-----|
| Python loops over candles | Slow strategy signal generation | Vectorize with pandas/numpy masks |
| Repeated DataFrame slicing | Heavy `.loc[]` / `.iloc[]` in loops | Precompute columns or arrays once |
| Large data in memory | Memory errors on 100k+ candles | Chunk data or use generators |
| Indicator recalculation | Same rolling/EMA recomputed many times | Cache as DataFrame columns |
| Excessive object/string conversion | Slow render/aggregation paths | Keep numeric dtypes until final display step |

### 3. Optimization Patterns

#### Vectorize Instead of Loop
```python
# ❌ Slow
for i in range(len(data)):
    if data.iloc[i]['Close'] > data.iloc[i]['SMA']:
        signals[i] = 1

# ✅ Fast
signals = (data['Close'] > data['SMA']).astype(int)
```

#### Cache Calculations
```python
# ❌ Slow (recalculates each iteration)
while backtest_running:
    sma = data['close'].rolling(20).mean()

# ✅ Fast (calculate once)
data['sma'] = data['close'].rolling(20).mean()
while backtest_running:
    sma = data['sma'].iloc[current_bar]
```

#### Efficient Type Handling
```python
# ✅ Set dtypes early
data = pd.read_csv('trades.csv', dtype={
    'Open': 'float32',
    'High': 'float32',
    'Low': 'float32',
    'Close': 'float32',
    'Volume': 'int32'
})
```

#### Numba / Cython Optimization
```python
from numba import njit

@njit
def fast_indicator_calc(prices):
    # JIT compiled loop for ultra-fast performance
    pass
```

### 4. Before/After Validation

After optimizing:
 - Results unchanged (same trades and metrics for same inputs)
 - Runtime improved with measured benchmark evidence
 - Memory impact measured and acceptable
 - Code remains maintainable

## Report Format

- Baseline runtime and memory
- Top bottlenecks (function-level)
- Chosen optimization and rationale
- Post-change benchmark and correctness parity check
