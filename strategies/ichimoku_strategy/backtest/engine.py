from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from strategies.ichimoku_strategy.backtest.metrics import compute_metrics
from strategies.ichimoku_strategy.execution.risk import calculate_position_size


@dataclass
class BacktestResult:
    trades: pd.DataFrame
    equity_curve: pd.Series
    metrics: dict


def run_backtest(
    df: pd.DataFrame,
    initial_capital: float = 500_000,
    commission: float = 0.0003,
    slippage_pct: float = 0.0002,
) -> BacktestResult:
    cash = initial_capital
    position = 0
    entry = 0.0
    trades: list[dict] = []
    equity: list[float] = []

    for i, row in enumerate(df.itertuples()):
        signal = int(row.signal)
        close = float(row.close)
        atr = float(row.atr) if hasattr(row, "atr") else 0.0

        if position == 0 and signal != 0 and atr > 0:
            stop = close - 1.5 * atr if signal == 1 else close + 1.5 * atr
            size = calculate_position_size(cash, close, stop, 1.0)
            if size > 0:
                entry = close * (1 + slippage_pct if signal == 1 else 1 - slippage_pct)
                position = signal * size
                cash -= abs(position) * entry * commission
        elif position != 0 and signal == -1 * (1 if position > 0 else -1):
            exit_price = close * (1 - slippage_pct if position > 0 else 1 + slippage_pct)
            pnl = (exit_price - entry) * position
            cash += pnl - abs(position) * exit_price * commission
            trades.append({"bar": i, "pnl": pnl})
            position = 0
            entry = 0.0

        equity.append(cash + position * close)

    equity_curve = pd.Series(equity, index=df.index)
    returns = equity_curve.pct_change().dropna()
    trades_df = pd.DataFrame(trades)
    metrics = compute_metrics(equity_curve, returns, trades_df)
    return BacktestResult(trades=trades_df, equity_curve=equity_curve, metrics=metrics)

