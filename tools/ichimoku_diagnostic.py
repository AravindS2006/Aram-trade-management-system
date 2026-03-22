from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from core.backtester import IntradayBacktester
from core.data_handler import DataHandler
from strategies.ichimoku_strategy import IchimokuRSIVWAPStrategy


def run_diag(start: str, end: str, interval: str = "1m") -> None:
    handler = DataHandler()
    df = handler.load_historical_csv("data/RELIANCE_minute.csv", start, end, interval)

    strategy = IchimokuRSIVWAPStrategy(
        df,
        params={
            "min_signal_score": 5,
            "cooldown_bars": 5,
            "max_daily_trades": 3,
            "allow_short": True,
        },
    )
    data_with_signals = strategy.get_data_with_signals()

    backtester = IntradayBacktester(
        data_with_signals,
        initial_capital=50_000,
        risk_per_trade_pct=0.005,
        sl_pct=0.01,
        tp_pct=0.02,
        tsl_pct=0.005,
        slippage=0.0005,
        commission=20,
    )
    tearsheet, metrics = backtester.run()

    signal_count = int((data_with_signals["signal"] != 0).sum())
    print(f"signals={signal_count}")
    print(f"metrics={metrics}")
    if tearsheet is not None and not tearsheet.empty:
        print(f"tag_counts={tearsheet['Tag'].value_counts().to_dict()}")
        print(f"gross_sum={round(float(tearsheet['Gross PnL'].sum()), 2)}")
        print(f"charges_sum={round(float(tearsheet['Taxes & Charges'].sum()), 2)}")
        print(f"net_sum={round(float(tearsheet['Net PnL'].sum()), 2)}")


if __name__ == "__main__":
    run_diag("2024-01-01", "2024-12-31", "1m")
