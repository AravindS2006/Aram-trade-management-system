from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.ichimoku_strategy.config import ATR_PERIOD, BARS_PER_SESSION_5M


def calculate_atr(df: pd.DataFrame, period: int = ATR_PERIOD) -> pd.DataFrame:
    """Calculate ATR, volatility regime, and ATR percentage of price."""
    out = df.copy()
    prev_close = out["close"].shift(1)
    tr = pd.concat(
        [
            out["high"] - out["low"],
            (out["high"] - prev_close).abs(),
            (out["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    out["true_range"] = tr
    out["atr"] = out["true_range"].ewm(alpha=1 / period, adjust=False).mean()
    out["atr_20d_avg"] = out["atr"].rolling(20 * BARS_PER_SESSION_5M, min_periods=1).mean()
    out["volatility_regime"] = np.where(out["atr"] > out["atr_20d_avg"], "trending", "ranging")
    out["atr_pct"] = (out["atr"] / out["close"].replace(0, np.nan)) * 100
    return out

