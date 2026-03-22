"""Central configuration for the Weapon Candle strategy."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time


@dataclass(frozen=True)
class WeaponCandleConfig:
    """All strategy constants in one immutable container."""

    EMA_FAST: int = 9
    EMA_MID: int = 21
    EMA_SLOW: int = 50

    MACD_FAST: int = 12
    MACD_SLOW: int = 26
    MACD_SIGNAL: int = 9

    RSI_PERIOD: int = 14
    RSI_LONG_LO: float = 45.0
    RSI_LONG_HI: float = 72.0
    RSI_SHORT_LO: float = 28.0
    RSI_SHORT_HI: float = 55.0

    BB_PERIOD: int = 20
    BB_STD: float = 2.0
    BB_SQUEEZE_RATIO: float = 0.008

    ATR_PERIOD: int = 14
    ATR_SL_MULT: float = 1.4
    ATR_AVG_DAYS: int = 20
    BARS_PER_DAY_5M: int = 75

    ENTRY_START: time = time(9, 30)
    ENTRY_END1: time = time(11, 30)
    ENTRY_START2: time = time(13, 0)
    ENTRY_END2: time = time(14, 0)
    HARD_EXIT: time = time(15, 15)

    CAPITAL: float = 500000.0
    RISK_PCT: float = 0.005
    RR1: float = 1.8
    RR2: float = 3.0
    T1_CLOSE_PCT: float = 0.50
    COMMISSION_PCT: float = 0.0003
    SLIPPAGE_PCT: float = 0.0002
    MAX_DAILY_TRADES: int = 4
    MIN_SCORE: int = 6
    HALF_SCORE: int = 4
    MAX_TRADE_LOSS: float = 0.02

    RVOL_PERIOD: int = 20
    HIGH_RVOL_THRESHOLD: float = 1.5
    MIN_SL_PCT: float = 0.002
    POSITION_CAPITAL_LIMIT_PCT: float = 0.15

    REQUIRED_COLUMNS: tuple[str, ...] = (
        "open",
        "high",
        "low",
        "close",
        "volume",
    )
    SCORE_REQUIRED_COLUMNS: tuple[str, ...] = (
        "ema9",
        "ema21",
        "ema50",
        "macd_hist",
        "rsi",
        "vwap",
        "atr",
        "bb_width",
    )


CFG = WeaponCandleConfig()
