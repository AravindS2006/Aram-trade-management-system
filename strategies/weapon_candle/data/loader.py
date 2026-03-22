"""Data loading and 1m->5m preparation for Weapon Candle."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pandas as pd

from strategies.weapon_candle.config import WeaponCandleConfig


def load_and_prepare(
    path: str | Path,
    cfg: WeaponCandleConfig,
    sep: str = "\t",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load DD/MM/YYYY HH:MM CSV and return (df_1m, df_5m)."""
    df = pd.read_csv(
        path,
        sep=sep,
        names=["date", "open", "high", "low", "close", "volume"],
        header=0,
        dtype={
            "open": float,
            "high": float,
            "low": float,
            "close": float,
            "volume": int,
        },
    )
    df["date"] = pd.to_datetime(df["date"], format="%d/%m/%Y %H:%M")
    df = df.set_index("date").sort_index()
    idx = cast(pd.DatetimeIndex, pd.DatetimeIndex(df.index))
    if idx.tz is None:
        idx = idx.tz_localize("Asia/Kolkata", nonexistent="shift_forward", ambiguous="NaT")
    else:
        idx = idx.tz_convert("Asia/Kolkata")
    df.index = idx

    df_1m = df.copy()
    df_5m = (
        df.resample("5min", closed="left", label="left")
        .agg(
            {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
            }
        )
        .dropna()
    )

    for frame in (df_1m, df_5m):
        frame["session_date"] = pd.Series(frame.index, index=frame.index).dt.date
        frame["prev_close"] = frame["close"].shift(1)

    assert (df_5m["high"] >= df_5m["low"]).all(), "Bad data: high < low"
    assert (df_5m["volume"] > 0).mean() > 0.95, "Too many zero-volume bars"

    return df_1m, df_5m
