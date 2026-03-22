"""Session-reset VWAP for E-ORB strategy."""

from __future__ import annotations

import pandas as pd

from strategies.eorb_strategy.config import VWAP_BAND_STD


def calculate_vwap(df: pd.DataFrame, band_std: float = VWAP_BAND_STD) -> pd.DataFrame:
    """Compute VWAP with daily session reset at 09:15 IST and standard deviation bands.

    Adds columns: vwap, vwap_upper1, vwap_lower1.
    CRITICAL: VWAP resets each day — never carried forward across sessions.
    """
    out = df.copy()
    out = out.sort_index()

    if out.index.tz is None:
        out.index = out.index.tz_localize("Asia/Kolkata")

    out["session_date"] = out.index.tz_convert("Asia/Kolkata").date
    out["typical_price"] = (out["high"] + out["low"] + out["close"]) / 3.0
    out["_tp_vol"] = out["typical_price"] * out["volume"]

    grp = out.groupby("session_date", group_keys=False)
    cum_tp_vol = grp["_tp_vol"].cumsum()
    cum_vol = grp["volume"].cumsum()
    out["vwap"] = cum_tp_vol / cum_vol.replace(0, float("nan"))

    session_std = (
        grp["typical_price"]
        .expanding()
        .std()
        .reset_index(level=0, drop=True)
        .fillna(0.0)
    )
    out["vwap_upper1"] = out["vwap"] + band_std * session_std
    out["vwap_lower1"] = out["vwap"] - band_std * session_std

    out = out.drop(columns=["_tp_vol"])
    return out
