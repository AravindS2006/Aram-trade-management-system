from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from core.backtester import IntradayBacktester
from core.data_handler import DataHandler
from strategies.ichimoku_strategy import IchimokuRSIVWAPStrategy

handler = DataHandler()
df = handler.load_historical_csv("data/RELIANCE_minute.csv", "2024-01-01", "2024-12-31", "5m")
strategy = IchimokuRSIVWAPStrategy(
    df,
    params={
        "min_signal_score": 5,
        "cooldown_bars": 3,
        "max_daily_trades": 2,
        "allow_short": False,
    },
)
data_with_signals = strategy.get_data_with_signals()

cases = [
    (0.01, 0.02, 0.005),
    (0.008, 0.012, 0.004),
    (0.007, 0.010, 0.0035),
    (0.006, 0.009, 0.003),
]

for sl, tp, tsl in cases:
    _, metrics = IntradayBacktester(
        data_with_signals,
        initial_capital=50_000,
        risk_per_trade_pct=0.005,
        sl_pct=sl,
        tp_pct=tp,
        tsl_pct=tsl,
        slippage=0.0005,
        commission=20,
    ).run()
    print(
        "sl=", sl,
        "tp=", tp,
        "tsl=", tsl,
        "ret=", metrics.get("Total Return %"),
        "trades=", metrics.get("Total Trades"),
        "pf=", metrics.get("Profit Factor"),
        "wr=", metrics.get("Win Rate %"),
        "charges=", metrics.get("Total Charges Paid"),
    )
