"""Entry signal checks for E-ORB strategy — implements all 6 mandatory gates."""

from __future__ import annotations

import pandas as pd

from strategies.eorb_strategy.config import (
    MAX_DAILY_TRADES,
    ORB_BUFFER_PCT,
    RVOL_MIN,
    VIX_MAX,
    VIX_MIN,
)
from strategies.eorb_strategy.indicators.adx import adx_signal
from strategies.eorb_strategy.utils.time_filter import is_valid_entry_window


def check_entry(
    df: pd.DataFrame,
    orb: dict,
    idx: int,
    direction: str,
    daily_trades: int,
    vix_today: float,
) -> dict:
    """Check all mandatory entry gates for an E-ORB signal.

    Six mandatory checks in order — returns early on first failure.

    Returns
    -------
    dict with keys: signal (bool), score (int), reason (str), entry_price (float)
    """
    fail = {"signal": False, "score": 0, "reason": "", "entry_price": 0.0}

    row = df.iloc[idx]
    ts = df.index[idx]

    # Step 1: Time gate
    if not is_valid_entry_window(ts):
        fail["reason"] = "outside_entry_window"
        return fail

    # Step 2: VIX gate
    if not (VIX_MIN <= vix_today <= VIX_MAX):
        fail["reason"] = "vix_out_of_range"
        return fail

    # Step 3: ORB validity
    if not orb.get("orb_valid", False):
        fail["reason"] = "orb_invalid"
        return fail

    close = float(row["close"])
    orb_high = orb["orb_high"]
    orb_low = orb["orb_low"]

    # Step 4: Breakout detection — candle close confirmation
    if direction == "long":
        breakout_level = orb_high * (1 + ORB_BUFFER_PCT)
        if close <= breakout_level:
            fail["reason"] = "no_long_breakout"
            return fail
    else:
        breakout_level = orb_low * (1 - ORB_BUFFER_PCT)
        if close >= breakout_level:
            fail["reason"] = "no_short_breakout"
            return fail

    # Step 5: ADX gate — ADX >= 25 and DI confirmation
    if not adx_signal(row, direction):
        fail["reason"] = "adx_gate_fail"
        return fail

    # Step 6: VWAP gate — institutional flow confirmation
    vwap_val = float(row.get("vwap", 0))
    if direction == "long" and close <= vwap_val:
        fail["reason"] = "vwap_long_fail"
        return fail
    if direction == "short" and close >= vwap_val:
        fail["reason"] = "vwap_short_fail"
        return fail

    # Step 7: RVOL gate — volume expansion
    rvol_val = float(row.get("rvol", 0))
    if rvol_val < RVOL_MIN:
        fail["reason"] = "rvol_too_low"
        return fail

    # Step 8: Daily trade cap
    if daily_trades >= MAX_DAILY_TRADES:
        fail["reason"] = "trade_cap_reached"
        return fail

    # All gates passed — compute score (caller uses scorer module)
    # Entry price will be next bar's open (handled by caller)
    return {
        "signal": True,
        "score": 0,  # Scorer computes this separately
        "reason": "all_gates_passed",
        "entry_price": 0.0,  # Caller sets from next bar open
    }
