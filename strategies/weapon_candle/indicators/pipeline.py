"""Indicator pipeline in canonical execution order."""

from __future__ import annotations

import pandas as pd

from strategies.weapon_candle.config import WeaponCandleConfig
from strategies.weapon_candle.indicators.atr import calculate_atr
from strategies.weapon_candle.indicators.bollinger import calculate_bollinger
from strategies.weapon_candle.indicators.ema import calculate_ema
from strategies.weapon_candle.indicators.macd import calculate_macd
from strategies.weapon_candle.indicators.rsi import calculate_rsi
from strategies.weapon_candle.indicators.volume import calculate_volume
from strategies.weapon_candle.indicators.vwap import calculate_vwap


def apply_all_indicators(df: pd.DataFrame, cfg: WeaponCandleConfig) -> pd.DataFrame:
    """Apply all seven indicators in documented order."""
    out = calculate_ema(df, cfg)
    out = calculate_macd(out, cfg)
    out = calculate_rsi(out, cfg)
    out = calculate_vwap(out, cfg)
    out = calculate_atr(out, cfg)
    out = calculate_bollinger(out, cfg)
    out = calculate_volume(out, cfg)
    return out
