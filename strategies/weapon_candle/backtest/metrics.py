"""Performance metrics for Weapon Candle backtests."""

from __future__ import annotations

import math

import numpy as np


def compute_metrics(trades: list[dict[str, object]], equity_curve: list[float]) -> dict[str, float]:
    """Compute required metrics table from closed trades and equity curve."""
    if not trades or len(equity_curve) < 2:
        return {
            "Win Rate %": 0.0,
            "Profit Factor": 0.0,
            "Sharpe": 0.0,
            "Sortino": 0.0,
            "Max Drawdown %": 0.0,
            "Avg RR": 0.0,
            "CAGR": 0.0,
            "Calmar": 0.0,
        }

    pnl_values: list[float] = []
    for trade in trades:
        value = trade.get("pnl", 0.0)
        pnl_values.append(float(value) if isinstance(value, (int, float)) else 0.0)
    pnls = np.array(pnl_values, dtype=float)
    wins = pnls[pnls > 0]
    losses = pnls[pnls < 0]

    gross_profit = float(wins.sum()) if wins.size else 0.0
    gross_loss = abs(float(losses.sum())) if losses.size else 0.0
    win_rate = (len(wins) / len(pnls)) * 100.0
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else math.inf

    returns = np.diff(np.array(equity_curve, dtype=float)) / np.array(
        equity_curve[:-1], dtype=float
    )
    mean_ret = float(np.mean(returns)) if returns.size else 0.0
    std_ret = float(np.std(returns, ddof=1)) if returns.size > 1 else 0.0
    downside = returns[returns < 0]
    downside_std = float(np.std(downside, ddof=1)) if downside.size > 1 else 0.0
    annual_factor = math.sqrt(252.0 * 75.0)

    sharpe = (mean_ret / std_ret) * annual_factor if std_ret > 0 else 0.0
    sortino = (mean_ret / downside_std) * annual_factor if downside_std > 0 else 0.0

    eq = np.array(equity_curve, dtype=float)
    peaks = np.maximum.accumulate(eq)
    dd = np.where(peaks > 0, (peaks - eq) / peaks, 0.0)
    max_drawdown_pct = float(np.max(dd) * 100.0)

    avg_win = float(np.mean(wins)) if wins.size else 0.0
    avg_loss = abs(float(np.mean(losses))) if losses.size else 0.0
    avg_rr = (avg_win / avg_loss) if avg_loss > 0 else math.inf

    initial = float(eq[0])
    final = float(eq[-1])
    periods = max(len(eq) - 1, 1)
    days = max(periods / 75.0, 1.0)
    cagr = ((final / initial) ** (365.0 / days)) - 1.0 if initial > 0 else 0.0
    calmar = (cagr / (max_drawdown_pct / 100.0)) if max_drawdown_pct > 0 else 0.0

    return {
        "Win Rate %": win_rate,
        "Profit Factor": profit_factor,
        "Sharpe": sharpe,
        "Sortino": sortino,
        "Max Drawdown %": max_drawdown_pct,
        "Avg RR": avg_rr,
        "CAGR": cagr,
        "Calmar": calmar,
    }
