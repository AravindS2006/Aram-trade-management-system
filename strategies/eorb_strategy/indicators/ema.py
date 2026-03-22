"""EMA trend filter for E-ORB strategy."""

from __future__ import annotations

import pandas as pd

from strategies.eorb_strategy.config import EMA_FAST, EMA_SLOW


def calculate_ema(df: pd.DataFrame, fast: int = EMA_FAST, slow: int = EMA_SLOW) -> pd.DataFrame:
    """Calculate EMA 9/21 on 5-min chart for trend alignment.

    Adds columns: ema_fast, ema_slow, ema_trend_bull, ema_trend_bear.
    """
    out = df.copy()
    out["ema_fast"] = out["close"].ewm(span=fast, adjust=False).mean()
    out["ema_slow"] = out["close"].ewm(span=slow, adjust=False).mean()
    out["ema_trend_bull"] = (out["ema_fast"] > out["ema_slow"]).astype(int)
    out["ema_trend_bear"] = (out["ema_fast"] < out["ema_slow"]).astype(int)
    return out
