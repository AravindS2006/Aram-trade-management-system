from __future__ import annotations

import numpy as np
import pandas as pd


def compute_metrics(equity_curve: pd.Series, returns: pd.Series, trades_df: pd.DataFrame) -> dict:
    if equity_curve.empty:
        return {}

    peak = equity_curve.cummax()
    drawdown = (equity_curve - peak) / peak
    max_drawdown = float(drawdown.min()) if len(drawdown) else 0.0

    mean_ret = returns.mean() if len(returns) else 0.0
    std_ret = returns.std() if len(returns) else 0.0
    sharpe = float((mean_ret / std_ret) * np.sqrt(252)) if std_ret and std_ret > 0 else 0.0

    wins = trades_df[trades_df["pnl"] > 0] if not trades_df.empty else pd.DataFrame()
    losses = trades_df[trades_df["pnl"] < 0] if not trades_df.empty else pd.DataFrame()
    gross_profit = float(wins["pnl"].sum()) if not wins.empty else 0.0
    gross_loss = abs(float(losses["pnl"].sum())) if not losses.empty else 0.0
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0.0

    return {
        "final_equity": float(equity_curve.iloc[-1]),
        "max_drawdown": max_drawdown,
        "sharpe": sharpe,
        "profit_factor": profit_factor,
        "win_rate": float((len(wins) / len(trades_df)) * 100) if len(trades_df) else 0.0,
    }

