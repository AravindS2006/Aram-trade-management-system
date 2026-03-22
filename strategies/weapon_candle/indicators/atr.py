"""Wilder ATR and volatility regime."""

from __future__ import annotations

import pandas as pd

from strategies.weapon_candle.config import WeaponCandleConfig


def calculate_atr(df: pd.DataFrame, cfg: WeaponCandleConfig) -> pd.DataFrame:
    """Compute ATR with Wilder smoothing and long-run average."""
    out = df.copy()
    tr = pd.concat(
        [
            out["high"] - out["low"],
            (out["high"] - out["prev_close"]).abs(),
            (out["low"] - out["prev_close"]).abs(),
        ],
        axis=1,
    ).max(axis=1)

    out["atr"] = tr.ewm(alpha=1 / cfg.ATR_PERIOD, adjust=False).mean()
    atr_window = cfg.ATR_AVG_DAYS * cfg.BARS_PER_DAY_5M
    out["atr_avg"] = out["atr"].rolling(atr_window).mean()
    out["trending"] = (out["atr"] > out["atr_avg"]).astype(int)
    return out
