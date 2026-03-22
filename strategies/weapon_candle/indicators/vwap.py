"""Session-reset VWAP and standard-deviation bands."""

from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.weapon_candle.config import WeaponCandleConfig


def calculate_vwap(df: pd.DataFrame, _cfg: WeaponCandleConfig) -> pd.DataFrame:
    """Compute per-session VWAP and +/-1 std bands."""
    out = df.copy()
    out["tp"] = (out["high"] + out["low"] + out["close"]) / 3.0
    out["vwap"] = np.nan
    out["vwap_std"] = np.nan

    for _, group in out.groupby("session_date"):
        cum_tpv = (group["tp"] * group["volume"]).cumsum()
        cum_vol = group["volume"].cumsum()
        vwap_session = cum_tpv / cum_vol
        std_session = group["tp"].expanding().std().fillna(0.0)
        out.loc[group.index, "vwap"] = vwap_session
        out.loc[group.index, "vwap_std"] = std_session

    out["vwap_upper"] = out["vwap"] + out["vwap_std"]
    out["vwap_lower"] = out["vwap"] - out["vwap_std"]
    out["above_vwap"] = (out["close"] > out["vwap"]).astype(int)
    return out
