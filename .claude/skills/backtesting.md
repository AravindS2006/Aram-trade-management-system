# Skill: Backtesting Engine — Aram-TMS

## Available Engines
1. **VectorBT** — `src/backtesting/vectorbt_runner.py` — fast, parameter optimization
2. **Backtrader** — `src/backtesting/backtrader_runner.py` — event-driven, realistic fills
3. **Zipline-Reloaded** — institutional pipeline-based

## Data Sources
### Short-Term (<2 years): yFinance
```python
from src.data.yfinance_loader import YFinanceLoader
loader = YFinanceLoader()
data = loader.fetch("RELIANCE.NS", start="2023-01-01", end="2024-12-31", interval="1d")
```

### Long-Term (>2 years): Kaggle CSV
```python
from src.data.csv_loader import KaggleCSVLoader
loader = KaggleCSVLoader(data_dir="data/raw/csv/")
data = loader.load("RELIANCE", start="2010-01-01", end="2024-12-31")
# Expected CSV columns: Date, Open, High, Low, Close, Volume
```

## Indian Transaction Costs — ALWAYS Include
```yaml
brokerage: 20          # Rs.20 flat per order (Dhan)
stt_sell: 0.001        # 0.1% on sell (delivery)
exchange_charges: 0.0000345
sebi_charges: 0.000001
gst: 0.18              # On brokerage + exchange
stamp_duty_buy: 0.00015
slippage: 0.0005       # 0.05%
```

## CLI Usage
```bash
python scripts/run_backtest.py --strategy MomentumStrategy
python scripts/run_backtest.py --strategy MomentumStrategy --start 2018-01-01 --end 2024-12-31
python scripts/run_backtest.py --strategy MomentumStrategy --mode walk_forward
python scripts/run_backtest.py --list-strategies
```

## Performance Metrics — Always Report
```
Total Return (%)       CAGR (%)
Sharpe (rf=6.5%)      Sortino Ratio
Calmar Ratio          Max Drawdown (%)
Win Rate (%)          Profit Factor
Expectancy/trade      Num Trades
Avg Holding Days      Benchmark vs NIFTY 50
```

## Walk-Forward Optimization
```python
from src.backtesting.walk_forward import WalkForwardOptimizer
optimizer = WalkForwardOptimizer(
    strategy_class=MomentumStrategy,
    param_grid={"lookback": [126, 189, 252], "ema_period": [30, 50, 100]},
    train_window=252,
    test_window=63,
    metric="sharpe"
)
results = optimizer.run(data)
```

## Quality Thresholds
- Sharpe > 1.5: Good | > 2.0: Excellent
- Max DD < 20%: Aggressive | < 10%: Institutional
- Profit Factor > 1.5: Robust
- Calmar > 1.0: Good risk-adjusted return

## Common Pitfalls
1. Look-ahead bias — always `signal.shift(1)` before backtesting
2. Survivorship bias — load historical constituents, not just current
3. Ignoring costs — always include all Indian market taxes
4. Overfitting — use walk-forward, not simple in-sample optimization
5. Illiquidity — filter stocks with < Rs.1Cr daily turnover
