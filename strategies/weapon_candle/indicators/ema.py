"""EMA stack and cross signals."""

from __future__ import annotations

import pandas as pd

from strategies.weapon_candle.config import WeaponCandleConfig


def calculate_ema(df: pd.DataFrame, cfg: WeaponCandleConfig) -> pd.DataFrame:
    """Compute EMA(9/21/50) and alignment/cross flags."""
    out = df.copy()
    c = out["close"]
    out["ema9"] = c.ewm(span=cfg.EMA_FAST, adjust=False).mean()
    out["ema21"] = c.ewm(span=cfg.EMA_MID, adjust=False).mean()
    out["ema50"] = c.ewm(span=cfg.EMA_SLOW, adjust=False).mean()

    out["ema_bull"] = ((out["ema9"] > out["ema21"]) & (out["ema21"] > out["ema50"])).astype(int)
    out["ema_bear"] = ((out["ema9"] < out["ema21"]) & (out["ema21"] < out["ema50"])).astype(int)
    out["ema9_cross_bull"] = (
        (out["ema9"] > out["ema21"]) & (out["ema9"].shift(1) <= out["ema21"].shift(1))
    ).astype(int)
    out["ema9_cross_bear"] = (
        (out["ema9"] < out["ema21"]) & (out["ema9"].shift(1) >= out["ema21"].shift(1))
    ).astype(int)
    return out
