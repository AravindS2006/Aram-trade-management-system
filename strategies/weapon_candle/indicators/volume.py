"""Relative volume calculations."""

from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.weapon_candle.config import WeaponCandleConfig


def calculate_volume(df: pd.DataFrame, cfg: WeaponCandleConfig) -> pd.DataFrame:
    """Compute RVOL as volume divided by rolling average volume."""
    out = df.copy()
    out["vol_ma20"] = out["volume"].rolling(cfg.RVOL_PERIOD).mean()
    out["rvol"] = out["volume"] / out["vol_ma20"].replace(0, np.nan)
    return out
