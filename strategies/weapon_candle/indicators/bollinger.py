"""Bollinger Bands and squeeze detection."""

from __future__ import annotations

import pandas as pd

from strategies.weapon_candle.config import WeaponCandleConfig


def calculate_bollinger(df: pd.DataFrame, cfg: WeaponCandleConfig) -> pd.DataFrame:
    """Compute BB(20,2) and squeeze flag from normalized width."""
    out = df.copy()
    c = out["close"]
    mid = c.rolling(cfg.BB_PERIOD).mean()
    std = c.rolling(cfg.BB_PERIOD).std()

    out["bb_upper"] = mid + (cfg.BB_STD * std)
    out["bb_lower"] = mid - (cfg.BB_STD * std)
    out["bb_mid"] = mid
    out["bb_width"] = (out["bb_upper"] - out["bb_lower"]) / c
    out["bb_squeeze"] = (out["bb_width"] < cfg.BB_SQUEEZE_RATIO).astype(int)
    return out
