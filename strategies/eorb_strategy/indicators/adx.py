"""Wilder's ADX indicator for E-ORB strategy."""

from __future__ import annotations

import pandas as pd

from strategies.eorb_strategy.config import ADX_MIN_THRESHOLD, ADX_PERIOD


def calculate_adx(df: pd.DataFrame, period: int = ADX_PERIOD) -> pd.DataFrame:
    """Calculate ADX using Wilder's smoothing (ewm alpha=1/period).

    Adds columns: true_range, plus_dm, minus_dm, atr, plus_di, minus_di, dx, adx.
    """
    out = df.copy()
    prev_close = out["close"].shift(1)
    prev_high = out["high"].shift(1)
    prev_low = out["low"].shift(1)

    # True Range
    tr1 = out["high"] - out["low"]
    tr2 = (out["high"] - prev_close).abs()
    tr3 = (out["low"] - prev_close).abs()
    out["true_range"] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # Directional Movement
    up_move = out["high"] - prev_high
    down_move = prev_low - out["low"]

    out["plus_dm"] = 0.0
    out["minus_dm"] = 0.0

    plus_mask = (up_move > down_move) & (up_move > 0)
    minus_mask = (down_move > up_move) & (down_move > 0)

    out.loc[plus_mask, "plus_dm"] = up_move[plus_mask]
    out.loc[minus_mask, "minus_dm"] = down_move[minus_mask]

    # Wilder smoothing
    alpha = 1.0 / period
    out["atr"] = out["true_range"].ewm(alpha=alpha, adjust=False).mean()
    smoothed_plus_dm = out["plus_dm"].ewm(alpha=alpha, adjust=False).mean()
    smoothed_minus_dm = out["minus_dm"].ewm(alpha=alpha, adjust=False).mean()

    # Directional Indicators
    out["plus_di"] = 100.0 * smoothed_plus_dm / out["atr"].replace(0, float("nan"))
    out["minus_di"] = 100.0 * smoothed_minus_dm / out["atr"].replace(0, float("nan"))

    # DX and ADX
    di_sum = out["plus_di"] + out["minus_di"]
    di_diff = (out["plus_di"] - out["minus_di"]).abs()
    out["dx"] = 100.0 * di_diff / di_sum.replace(0, float("nan"))
    out["adx"] = out["dx"].ewm(alpha=alpha, adjust=False).mean()

    return out


def adx_signal(row: pd.Series, direction: str) -> bool:
    """Return True if ADX >= threshold AND directional index confirms direction.

    direction='long':  plus_di  > minus_di
    direction='short': minus_di > plus_di
    """
    adx_val = float(row.get("adx", 0))
    if adx_val < ADX_MIN_THRESHOLD:
        return False

    plus_di = float(row.get("plus_di", 0))
    minus_di = float(row.get("minus_di", 0))

    if direction == "long":
        return plus_di > minus_di
    return minus_di > plus_di
