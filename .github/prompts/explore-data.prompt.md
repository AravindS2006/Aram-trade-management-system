---
name: explore-data
description: "Load, describe, and visualize trade data. Run exploratory data analysis with summary statistics and charts."
argument-hint: "<file-path> [analysis-depth: quick|standard|deep]"
---

# Explore Data Prompt

Perform comprehensive exploratory data analysis on trade datasets.

## Usage

```
/explore-data data/RELIANCE_trades.csv --analysis-depth standard
```

## EDA Workflow

### 1. Data Overview
- Load CSV and display shape
- Show columns and data types
- Display first/last rows
- Summary statistics

### 2. Data Quality Check
```
✓ NaN values: 0 (0%)
✓ Duplicate timestamps: 0
✓ Column validation:
  - open > 0: ✓
  - high >= open, close: ✓
  - low <= open, close: ✓
  - volume > 0: ✓
✓ Chronological order: ✓ (ascending timestamps)
```

### 3. Statistical Analysis
- Price statistics (mean, std, min, max)
- Return distribution (daily % changes)
- Volatility by period (rolling stdev)
- Volume statistics

### 4. Pattern Detection
- Trend analysis (3-month rolling average)
- Volatility clusters (high vol periods)
- Time-of-day patterns (if intraday data)
- Day-of-week effects
- Seasonal patterns

### 5. Visualization
- Price over time (line chart)
- Volume over time (bar chart)
- Returns distribution (histogram)
- Volatility over time (rolling std)
- Autocorrelation plot

## Output Example

```
═══════════════════════════════════════════════════════════════
                    DATA EXPLORATION REPORT
═══════════════════════════════════════════════════════════════

File: data/RELIANCE_trades.csv
Rows: 1,250 | Columns: 6 | Timespan: 2022-01-01 to 2024-12-31

─── DATA SUMMARY ────────────────────────────────────────────
        open        high         low       close      volume
Mean    2345.6      2389.2      2312.4     2354.1    1,250,000
Std      234.5       245.3       223.1      235.2      325,000
Min     1892.3      1923.4      1875.2     1901.2      180,000
Max     2899.1      2945.7      2876.3     2923.4    3,400,000

─── DATA QUALITY ────────────────────────────────────────────
Missing values: 0 ✓
Duplicates: 0 ✓
Valid prices: 100% ✓
Valid volume: 100% ✓

─── RETURNS ANALYSIS ────────────────────────────────────────
Daily return mean:  0.12%
Daily return std:   2.34%
Positive days:      56%
Negative days:      44%
Largest up day:     +8.5%
Largest down day:   -7.2%

─── PATTERNS ────────────────────────────────────────────────
Volatility regime:
  - Low vol periods (< 1%): 35 days
  - Normal vol (1-3%):      1,100 days
  - High vol (> 3%):        115 days

Day-of-week effect:
  - Monday:    +0.08% avg
  - Tuesday:   +0.15% avg
  - Wednesday: +0.05% avg
  - Thursday:  -0.02% avg
  - Friday:    +0.10% avg

═══════════════════════════════════════════════════════════════
```

## Analysis Depths

| Depth | Time | Includes |
|-------|------|----------|
| quick | 5 min | Data summary, quality check, basic stats |
| standard | 15 min | + Pattern detection, correlations |
| deep | 30+ min | + Regime analysis, seasonality, anomalies |

