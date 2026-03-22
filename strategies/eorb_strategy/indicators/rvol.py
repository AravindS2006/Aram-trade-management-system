"""Relative Volume (RVOL) indicator for E-ORB strategy."""

from __future__ import annotations

import pandas as pd

from strategies.eorb_strategy.config import RVOL_LOOKBACK


def calculate_rvol(df: pd.DataFrame, lookback: int = RVOL_LOOKBACK) -> pd.DataFrame:
    """Compute relative volume vs rolling average.

    Adds columns: vol_ma20, rvol.
    Breakout candle rvol must be >= 1.5 for a valid signal.
    """
    out = df.copy()
    out["vol_ma20"] = out["volume"].rolling(lookback, min_periods=1).mean()
    out["rvol"] = out["volume"] / out["vol_ma20"].replace(0, float("nan"))
    return out
