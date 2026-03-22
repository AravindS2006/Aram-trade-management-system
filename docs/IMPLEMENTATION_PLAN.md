# Aram-TMS Implementation Plan

## Phase 1: Backtesting + Forward Testing (CURRENT)

### Infrastructure
- [x] Directory structure
- [x] CLAUDE.md + 7 skill files
- [x] .env.example, .gitignore, requirements.txt
- [x] config/settings.yaml

### Data Layer
- [x] YFinanceLoader — short-term (<2yr), parquet caching, validation
- [x] KaggleCSVLoader — long-term Kaggle CSVs, auto column detection
- [ ] DhanHistoricalLoader — via DhanHQ API
- [ ] UniverseManager — NIFTY historical constituent management

### Strategy Framework
- [x] BaseStrategy abstract class + registry
- [x] MomentumStrategy (12-1 dual momentum + volume)
- [x] MeanReversionStrategy (Bollinger Bands + RSI)
- [x] BreakoutStrategy (Donchian Channel)
- [ ] FactorStrategy (multi-factor model)
- [ ] MLStrategy (XGBoost alpha signals)

### Backtesting Engines
- [x] VectorBTRunner — vectorized, fast, parameter optimization
- [x] BacktraderRunner — event-driven, realistic execution
- [x] WalkForwardOptimizer — rolling + anchored, prevents overfitting
- [ ] ZiplineRunner — institutional pipeline-based
- [ ] Monte Carlo simulation

### Risk Management
- [x] RiskManager — 11 pre-trade checks, circuit breakers
- [x] Position sizing — fixed fractional, Kelly, equal weight
- [ ] Portfolio VaR/CVaR calculation
- [ ] SEBI margin calculator

### Forward Testing
- [x] DhanSandboxClient — paper trading via DhanHQ sandbox
- [x] DhanSecurityMaster — symbol to security ID mapping
- [x] ForwardTestRunner — signal -> risk check -> sandbox order loop
- [ ] WebSocket real-time market feed
- [ ] Multi-strategy simultaneous forward testing

### Dashboard
- [x] Streamlit 8-page app (dark institutional theme)
- [x] Overview, Backtesting, Forward Test, Strategies, Risk Monitor pages
- [ ] Monthly returns calendar heatmap
- [ ] Sector exposure treemap
- [ ] Walk-forward visualization

## Phase 2: Live Trading (Future)
- Full OMS with bracket/cover/GTT orders
- DhanHQ WebSocket tick feed
- TWAP/VWAP execution algorithms
- Real-time Greeks for options

## Phase 3: Options & Derivatives (Future)
- Black-Scholes + IV calculation
- Iron Condor, Straddle, Calendar Spreads
- SPAN margin calculator

## Phase 4: ML Alpha (Future)
- XGBoost/LightGBM return prediction
- LSTM sequence modeling
- MLflow experiment tracking

## Running
```bash
pip install -r requirements.txt
cp .env.example .env
python scripts/run_backtest.py --strategy MomentumStrategy
streamlit run src/dashboard/app.py
```

## Performance Benchmarks
| Engine | 1yr/daily/NIFTY50 |
|---|---|
| VectorBT | ~0.5s |
| Backtrader | ~8s |

## Target Metrics
| Metric | Minimum | Target |
|---|---|---|
| Sharpe | 1.0 | 1.5+ |
| CAGR | 15% | 25%+ |
| Max DD | <20% | <12% |
