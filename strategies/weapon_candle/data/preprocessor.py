"""DataFrame validation and common derived fields."""

from __future__ import annotations

import pandas as pd

from strategies.weapon_candle.config import WeaponCandleConfig


def preprocess(df: pd.DataFrame, cfg: WeaponCandleConfig) -> pd.DataFrame:
    """Validate OHLCV input and add session_date/prev_close fields."""
    missing = [c for c in cfg.REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    out = df.copy()
    out["session_date"] = pd.Series(out.index, index=out.index).dt.date
    out["prev_close"] = out["close"].shift(1)

    bad_hl = int((out["high"] < out["low"]).sum())
    if bad_hl > 0:
        raise ValueError(f"{bad_hl} bars have high < low")

    return out
