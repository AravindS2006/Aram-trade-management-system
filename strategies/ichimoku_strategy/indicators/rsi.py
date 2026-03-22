from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.ichimoku_strategy.config import RSI_PERIOD


def calculate_rsi(df: pd.DataFrame, period: int = RSI_PERIOD) -> pd.DataFrame:
    """Calculate Wilder RSI and assign momentum zone labels."""
    out = df.copy()
    delta = out["close"].diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)

    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out["rsi"] = 100 - (100 / (1 + rs))

    out["rsi_zone"] = np.select(
        [
            out["rsi"] > 68,
            (out["rsi"] >= 50) & (out["rsi"] <= 68),
            (out["rsi"] >= 32) & (out["rsi"] < 50),
            out["rsi"] < 32,
        ],
        ["overbought", "long_zone", "neutral_short", "oversold"],
        default="neutral",
    )
    return out

