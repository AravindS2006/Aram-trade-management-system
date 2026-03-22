"""Opening Range builder for E-ORB strategy."""

from __future__ import annotations

from datetime import date, time

import pandas as pd

from strategies.eorb_strategy.config import (
    ORB_MAX_RANGE_PCT,
    ORB_MIN_RANGE_PCT,
    ORB_WINDOW_END,
    ORB_WINDOW_START,
)


def build_orb(df: pd.DataFrame, session_date: date | None = None) -> dict:
    """Build the Opening Range from the first 15-minute candle (09:15–09:30 IST).

    Parameters
    ----------
    df : pd.DataFrame
        5-min OHLCV DataFrame with DatetimeIndex (IST-aware).
    session_date : date | None
        If provided, filter to this specific session date.
        If None, use all rows between ORB_WINDOW_START and ORB_WINDOW_END.

    Returns
    -------
    dict with keys: orb_high, orb_low, orb_range, orb_mid, orb_range_pct,
                    orb_valid, orb_date.
    """
    if df.index.tz is None:
        raise ValueError("DataFrame index must be timezone-aware (IST).")

    orb_df = df.copy()

    if session_date is not None:
        orb_df = orb_df[orb_df.index.tz_convert("Asia/Kolkata").date == session_date]

    # Filter rows within the ORB window: 09:15:00 to 09:29:59
    orb_bars = orb_df[
        (orb_df.index.time >= ORB_WINDOW_START)
        & (orb_df.index.time < ORB_WINDOW_END)
    ]

    if orb_bars.empty:
        return {
            "orb_high": 0.0,
            "orb_low": 0.0,
            "orb_range": 0.0,
            "orb_mid": 0.0,
            "orb_range_pct": 0.0,
            "orb_valid": False,
            "orb_date": session_date,
        }

    orb_high = float(orb_bars["high"].max())
    orb_low = float(orb_bars["low"].min())
    orb_range = orb_high - orb_low
    orb_mid = (orb_high + orb_low) / 2.0
    orb_range_pct = (orb_range / orb_mid * 100.0) if orb_mid > 0 else 0.0

    orb_valid = ORB_MIN_RANGE_PCT <= orb_range_pct <= ORB_MAX_RANGE_PCT

    return {
        "orb_high": orb_high,
        "orb_low": orb_low,
        "orb_range": orb_range,
        "orb_mid": orb_mid,
        "orb_range_pct": orb_range_pct,
        "orb_valid": orb_valid,
        "orb_date": session_date,
    }
