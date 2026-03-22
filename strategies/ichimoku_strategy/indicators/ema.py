from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.ichimoku_strategy.config import EMA_FAST, EMA_SLOW


def calculate_ema(df: pd.DataFrame, fast: int = EMA_FAST, slow: int = EMA_SLOW) -> pd.DataFrame:
    """Calculate EMA 9/21 micro-entry signals on 1-minute data."""
    out = df.copy()
    out["ema_fast"] = out["close"].ewm(span=fast, adjust=False).mean()
    out["ema_slow"] = out["close"].ewm(span=slow, adjust=False).mean()
    out["ema_cross_val"] = out["ema_fast"] - out["ema_slow"]
    out["ema_cross_bull"] = (
        (out["ema_fast"].shift(1) <= out["ema_slow"].shift(1)) & (out["ema_fast"] > out["ema_slow"])
    ).astype(int)
    out["ema_cross_bear"] = (
        (out["ema_fast"].shift(1) >= out["ema_slow"].shift(1)) & (out["ema_fast"] < out["ema_slow"])
    ).astype(int)
    out["ema_aligned_bull"] = (out["ema_fast"] > out["ema_slow"]).astype(int)

    # Backward-compatible aliases
    out["ema_cross"] = np.sign(out["ema_cross_val"]).astype(int)
    out["ema_cross_signal"] = (out["ema_cross_bull"] == 1) | (out["ema_cross_bear"] == 1)
    return out


def confirm_micro_entry(df_1m: pd.DataFrame, direction: str) -> bool:
    """Return True when latest 1-minute EMA cross supports trade direction."""
    if df_1m.empty or "ema_cross" not in df_1m.columns:
        return False
    last = df_1m.iloc[-1]
    if direction == "long":
        return bool(last.get("ema_cross_bull", 0) == 1)
    return bool(last.get("ema_cross_bear", 0) == 1)

