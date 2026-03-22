"""Confluence scoring engine."""

from __future__ import annotations

import pandas as pd

from strategies.weapon_candle.config import WeaponCandleConfig


def score_signal(row: pd.Series, direction: str, cfg: WeaponCandleConfig) -> int:
    """Return score 0-10, or -1 on hard-fail conditions."""
    score = 0

    if direction == "long":
        if row["ema_bull"] != 1:
            return -1
        score += 2

        if row["macd_hist"] <= 0:
            return -1
        score += 2

        if row["macd_cross_bull"] == 1:
            score += 1
        if row["macd_above_zero"] == 1:
            score += 1

        if not (cfg.RSI_LONG_LO <= row["rsi"] <= cfg.RSI_LONG_HI):
            return -1
        score += 2

        if row["rsi_rising"] == 1:
            score += 1

        if row["above_vwap"] != 1:
            return -1
        score += 2

        if row["close"] > row["vwap_upper"]:
            score += 1

    elif direction == "short":
        if row["ema_bear"] != 1:
            return -1
        score += 2

        if row["macd_hist"] >= 0:
            return -1
        score += 2

        if row["macd_cross_bear"] == 1:
            score += 1
        if row["macd_above_zero"] == 0:
            score += 1

        if not (cfg.RSI_SHORT_LO <= row["rsi"] <= cfg.RSI_SHORT_HI):
            return -1
        score += 2

        if row["rsi_rising"] == 0:
            score += 1

        if row["above_vwap"] != 0:
            return -1
        score += 2

        if row["close"] < row["vwap_lower"]:
            score += 1

    else:
        raise ValueError(f"Unknown direction: {direction}")

    if row["bb_squeeze"] == 1:
        return -1

    if row["rvol"] >= cfg.HIGH_RVOL_THRESHOLD:
        score += 1
    if row["trending"] == 1:
        score += 1

    return min(score, 10)


def score_to_size_multiplier(score: int, cfg: WeaponCandleConfig) -> float:
    """Convert score to 0.0/0.5/1.0 size multiplier."""
    if score >= cfg.MIN_SCORE:
        return 1.0
    if score >= cfg.HALF_SCORE:
        return 0.5
    return 0.0
