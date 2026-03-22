"""MACD indicator and momentum expansion flags."""

from __future__ import annotations

import pandas as pd

from strategies.weapon_candle.config import WeaponCandleConfig


def calculate_macd(df: pd.DataFrame, cfg: WeaponCandleConfig) -> pd.DataFrame:
    """Compute MACD(12,26,9) with cross and histogram expansion flags."""
    out = df.copy()
    c = out["close"]
    ema_fast = c.ewm(span=cfg.MACD_FAST, adjust=False).mean()
    ema_slow = c.ewm(span=cfg.MACD_SLOW, adjust=False).mean()

    out["macd_line"] = ema_fast - ema_slow
    out["macd_signal"] = out["macd_line"].ewm(span=cfg.MACD_SIGNAL, adjust=False).mean()
    out["macd_hist"] = out["macd_line"] - out["macd_signal"]

    out["macd_cross_bull"] = (
        (out["macd_line"] > out["macd_signal"])
        & (out["macd_line"].shift(1) <= out["macd_signal"].shift(1))
    ).astype(int)
    out["macd_cross_bear"] = (
        (out["macd_line"] < out["macd_signal"])
        & (out["macd_line"].shift(1) >= out["macd_signal"].shift(1))
    ).astype(int)

    out["hist_exp_bull"] = (
        (out["macd_hist"] > 0) & (out["macd_hist"] > out["macd_hist"].shift(1))
    ).astype(int)
    out["hist_exp_bear"] = (
        (out["macd_hist"] < 0) & (out["macd_hist"] < out["macd_hist"].shift(1))
    ).astype(int)
    out["macd_above_zero"] = (out["macd_line"] > 0).astype(int)
    return out
