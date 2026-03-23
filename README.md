# Aram Trade Management System (Aram-TMS)

**Professional Institutional-Grade Algorithmic Trading System for Indian Markets**

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env          # Add DhanHQ credentials
python scripts/run_backtest.py --strategy MomentumStrategy
streamlit run src/dashboard/app.py
```

## UV Workflow (Offline-First)

Project tooling is configured for `uv` with linting, formatting, type checks, and tests.
No install step is required right now; run these later when network is stable:

```bash
# One-time dependency install (runtime + dev tools)
uv sync --all-groups

# Optional heavy extras
uv sync --all-groups --extra vectorized
uv sync --all-groups --extra ta-advanced

# Quality checks
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src
uv run pytest

# One-command quality check on Windows PowerShell
powershell -ExecutionPolicy Bypass -File scripts/dev_quality.ps1

# Security and maintainability scripts (Windows PowerShell)
powershell -ExecutionPolicy Bypass -File scripts/dev_security.ps1
powershell -ExecutionPolicy Bypass -File scripts/dev_maintainability.ps1
```

Pre-commit is configured with local hooks (no hook repo downloads):

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```

Additional quality and security tools (configured in pyproject, install later with uv sync):

```bash
# Security
uv run bandit -r src scripts
uv run pip-audit

# Dead code and maintainability
uv run vulture src scripts
uv run radon cc src -s -a

# Docstring coverage
uv run interrogate src
```

Model Context Protocol (MCP):
- No project-local MCP server is required for this repository right now.
- The current workflow uses editor-provided language tooling and does not depend on a custom MCP server process.

VS Code tasks are preconfigured in .vscode/tasks.json:
- Quality: Full
- Security: Scan
- Maintainability: Scan

## Features
- **Backtesting**: VectorBT (fast) + Backtrader (event-driven) + Walk-Forward Optimization
- **Data**: yFinance (<2yr) + Kaggle CSV (long-term) with Parquet caching
- **Forward Testing**: DhanHQ Sandbox paper trading
- **Live Trading**: DhanHQ Live API (Phase 2)
- **Dashboard**: Streamlit 8-page professional UI
- **Strategies**: Momentum, Mean Reversion, Breakout (extensible)
- **Risk**: 11 pre-trade checks, circuit breakers, Kelly/fixed-fractional sizing
- **Costs**: Accurate Indian market costs (STT, exchange charges, GST, stamp duty)

## Directory Structure
```
Aram-trade-management-system/
├── .claude/          # Claude agentic instructions + skill files
├── src/
│   ├── strategies/   # BaseStrategy + library (Momentum, MeanRev, Breakout)
│   ├── backtesting/  # VectorBT, Backtrader, Walk-Forward runners
│   ├── forward_testing/ # DhanHQ Sandbox client + runner
│   ├── data/         # yFinance + Kaggle CSV loaders
│   ├── risk/         # Risk manager + position sizing
│   └── dashboard/    # Streamlit app
├── config/           # settings.yaml
├── data/raw/csv/     # Place Kaggle CSV files here
├── scripts/          # CLI runners
└── tests/            # Unit + integration tests
```

## Strategies

| Strategy | Category | Universe |
|---|---|---|
| MomentumStrategy | 12-1 Momentum + Volume | NIFTY 100 |
| MeanReversionStrategy | Bollinger Bands + RSI | NIFTY 50 |
| BreakoutStrategy | Donchian Channel + Volume | NIFTY 100 |

## Creating a Strategy
```python
from src.strategies.base_strategy import BaseStrategy, register_strategy

@register_strategy
class MyStrategy(BaseStrategy):
    NAME = "MyStrategy"
    CATEGORY = "momentum"

    def __init__(self, lookback=20, **kwargs):
        super().__init__(**kwargs)
        self.lookback = lookback

    def get_parameters(self): return {"lookback": self.lookback}
    def validate_parameters(self): assert 5<=self.lookback<=200; return True

    def generate_signals(self, data):
        sma = data["Close"].rolling(self.lookback).mean()
        signals = (data["Close"] > sma).astype(int)
        return signals.shift(1).fillna(0).astype(int)  # ALWAYS shift!
```

## CLI Reference
```bash
python scripts/run_backtest.py --strategy MomentumStrategy --start 2018-01-01
python scripts/run_backtest.py --mode walk_forward --train-window 252 --test-window 63
python scripts/run_backtest.py --list-strategies
python scripts/run_forward_test.py --strategy MomentumStrategy --symbols RELIANCE TCS
streamlit run src/dashboard/app.py
```

## Disclaimer
For educational/personal use only. Algorithmic trading involves significant financial risk.
Past backtest performance does not guarantee future results.
