from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.ichimoku_strategy.config import (
    DISPLACEMENT,
    KIJUN_PERIOD,
    SENKOU_B_PERIOD,
    TENKAN_PERIOD,
)


def calculate_ichimoku(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate Ichimoku components and cloud-state helper columns."""
    out = df.copy()
    out["tenkan"] = (
        out["high"].rolling(TENKAN_PERIOD).max() + out["low"].rolling(TENKAN_PERIOD).min()
    ) / 2.0
    out["kijun"] = (
        out["high"].rolling(KIJUN_PERIOD).max() + out["low"].rolling(KIJUN_PERIOD).min()
    ) / 2.0
    out["senkou_a"] = ((out["tenkan"] + out["kijun"]) / 2.0).shift(DISPLACEMENT)
    out["senkou_b"] = (
        (out["high"].rolling(SENKOU_B_PERIOD).max() + out["low"].rolling(SENKOU_B_PERIOD).min())
        / 2.0
    ).shift(DISPLACEMENT)
    out["chikou"] = out["close"].shift(-DISPLACEMENT)

    out["cloud_top"] = np.maximum(out["senkou_a"], out["senkou_b"])
    out["cloud_bot"] = np.minimum(out["senkou_a"], out["senkou_b"])
    out["cloud_bull"] = (out["senkou_a"] > out["senkou_b"]).astype(int)
    out["cloud_thick"] = (out["senkou_a"] - out["senkou_b"]).abs() / out["close"].replace(0, np.nan)

    out["above_cloud"] = (out["close"] > out["cloud_top"]).astype(int)
    out["below_cloud"] = (out["close"] < out["cloud_bot"]).astype(int)
    out["inside_cloud"] = 1 - out["above_cloud"] - out["below_cloud"]

    bull_cross, bear_cross = tk_cross_signal(out)
    out["tk_cross_bull"] = bull_cross
    out["tk_cross_bear"] = bear_cross
    out["tk_diff"] = out["tenkan"] - out["kijun"]

    out["chikou_bull"] = (out["close"] > out["close"].shift(DISPLACEMENT)).astype(int)
    out["chikou_bear"] = (out["close"] < out["close"].shift(DISPLACEMENT)).astype(int)

    # Backward-compatible aliases
    out["cloud_color"] = np.where(out["cloud_bull"] == 1, "bullish", "bearish")
    out["cloud_thickness"] = out["cloud_thick"]
    out["price_vs_cloud"] = np.where(
        out["above_cloud"] == 1,
        "above",
        np.where(out["below_cloud"] == 1, "below", "inside"),
    )
    out["tk_cross"] = np.where(out["tk_cross_bull"] == 1, 1, np.where(out["tk_cross_bear"] == 1, -1, 0))
    return out


def cloud_color(df: pd.DataFrame) -> pd.Series:
    """Return bullish/bearish cloud color labels."""
    return np.where(df["cloud_bull"] == 1, "bullish", "bearish")


def price_vs_cloud(df: pd.DataFrame) -> pd.Series:
    """Return where price sits relative to cloud: above/below/inside."""
    return np.where(df["above_cloud"] == 1, "above", np.where(df["below_cloud"] == 1, "below", "inside"))


def cloud_thickness(df: pd.DataFrame) -> pd.Series:
    """Return normalized cloud thickness."""
    return df["cloud_thick"]


def tk_cross_signal(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Return tuple of (bull_cross, bear_cross) marker series."""
    prev_t = df["tenkan"].shift(1)
    prev_k = df["kijun"].shift(1)
    bullish = ((prev_t <= prev_k) & (df["tenkan"] > df["kijun"])).astype(int)
    bearish = ((prev_t >= prev_k) & (df["tenkan"] < df["kijun"])).astype(int)
    return bullish, bearish

