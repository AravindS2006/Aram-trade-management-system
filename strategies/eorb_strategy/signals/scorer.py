"""Signal quality scorer for E-ORB strategy (Section 6 scoring table)."""

from __future__ import annotations

import pandas as pd

from strategies.eorb_strategy.config import (
    ADX_MIN_THRESHOLD,
    ADX_STRONG,
    SCORE_A_MIN,
    SCORE_B_MIN,
    SCORE_C_MIN,
    VIX_MAX,
    VIX_MIN,
)


def score_signal(
    row: pd.Series,
    orb: dict,
    direction: str,
    vix_today: float,
    prev_day_high: float = 0.0,
    prev_day_low: float = 0.0,
) -> dict:
    """Score a signal 0–13 using the E-ORB scoring table.

    Returns dict with: total_score, grade, size_multiplier, execute,
                        adjusted_target_rr.
    """
    score = 0

    # ORB range in ideal width (0.3%–1.2%)
    orb_range_pct = orb.get("orb_range_pct", 0)
    if 0.3 <= orb_range_pct <= 1.2:
        score += 2

    # ADX strength
    adx_val = float(row.get("adx", 0))
    if adx_val >= ADX_STRONG:
        score += 2
    elif adx_val >= ADX_MIN_THRESHOLD:
        score += 1

    # Close above ORB high / below ORB low (mandatory — already verified by entry gate)
    score += 2

    # DI separation > 5 points
    plus_di = float(row.get("plus_di", 0))
    minus_di = float(row.get("minus_di", 0))
    if direction == "long" and (plus_di - minus_di) > 5:
        score += 1
    elif direction == "short" and (minus_di - plus_di) > 5:
        score += 1

    # VWAP confirmation (already verified by gate)
    score += 1

    # RVOL >= 2.0 (strong volume expansion)
    rvol = float(row.get("rvol", 0))
    if rvol >= 2.0:
        score += 1

    # EMA aligned
    if direction == "long" and int(row.get("ema_trend_bull", 0)) == 1:
        score += 1
    elif direction == "short" and int(row.get("ema_trend_bear", 0)) == 1:
        score += 1

    # Previous day high/low broken
    close = float(row.get("close", 0))
    if direction == "long" and prev_day_high > 0 and close > prev_day_high:
        score += 1
    elif direction == "short" and prev_day_low > 0 and close < prev_day_low:
        score += 1

    # VIX in ideal range (12–18)
    if 12 <= vix_today <= 18:
        score += 1

    # Grade and size multiplier
    if score >= SCORE_A_MIN:
        grade = "A"
        size_multiplier = 1.0
        target_rr = 2.5
    elif score >= SCORE_B_MIN:
        grade = "B"
        size_multiplier = 1.0
        target_rr = 2.0
    elif score >= SCORE_C_MIN:
        grade = "C"
        size_multiplier = 0.5
        target_rr = 1.5
    else:
        grade = "skip"
        size_multiplier = 0.0
        target_rr = 0.0

    return {
        "total_score": score,
        "grade": grade,
        "size_multiplier": size_multiplier,
        "execute": grade != "skip",
        "adjusted_target_rr": target_rr,
    }
