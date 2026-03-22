"""RSI using Wilder smoothing only."""

from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.weapon_candle.config import WeaponCandleConfig


def calculate_rsi(df: pd.DataFrame, cfg: WeaponCandleConfig) -> pd.DataFrame:
    """Compute RSI with Wilder EWM, not rolling mean."""
    out = df.copy()
    delta = out["close"].diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / cfg.RSI_PERIOD, adjust=False).mean()
    loss = (-delta).clip(lower=0).ewm(alpha=1 / cfg.RSI_PERIOD, adjust=False).mean()

    rs = gain / loss.replace(0, np.nan)
    out["rsi"] = 100 - (100 / (1 + rs))
    out["rsi_rising"] = (out["rsi"] > out["rsi"].shift(2)).astype(int)
    return out
