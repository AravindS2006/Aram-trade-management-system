from __future__ import annotations

import pandas as pd


def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    """Clean OHLCV data and add session-reset VWAP with bands."""
    out = df.copy()
    out = out.sort_index()

    if out.index.tz is None:
        out.index = out.index.tz_localize("Asia/Kolkata")

    out["session_date"] = out.index.tz_convert("Asia/Kolkata").date
    out["typical_price"] = (out["high"] + out["low"] + out["close"]) / 3.0
    out["tp_vol"] = out["typical_price"] * out["volume"]

    grp = out.groupby("session_date", group_keys=False)
    cum_tp_vol = grp["tp_vol"].cumsum()
    cum_vol = grp["volume"].cumsum()
    out["vwap"] = cum_tp_vol / cum_vol

    session_std = grp["typical_price"].expanding().std().reset_index(level=0, drop=True).fillna(0.0)
    out["vwap_upper1"] = out["vwap"] + session_std
    out["vwap_lower1"] = out["vwap"] - session_std
    out["vwap_upper2"] = out["vwap"] + 2.0 * session_std
    out["vwap_lower2"] = out["vwap"] - 2.0 * session_std

    # Fill only short gaps and never bridge larger missing runs.
    out = out.ffill(limit=2)

    out = out.drop(columns=["tp_vol"])

    return out

