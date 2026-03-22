"""
Built-in Strategies — Aram-TMS
Momentum, Mean Reversion, and Breakout strategies for NSE equities.
"""
from __future__ import annotations
from typing import Any, Dict
import numpy as np
import pandas as pd
from loguru import logger
from src.strategies.base_strategy import BaseStrategy, register_strategy


@register_strategy
class MomentumStrategy(BaseStrategy):
    """
    Dual Momentum Strategy with Volume Confirmation.

    Alpha Hypothesis:
        Stocks with strong 12-1 month momentum continue outperforming
        (Jegadeesh & Titman 1993). Volume confirmation filters noise.

    Signal: Long when 12-1M return > 0 AND price > EMA AND RSI < 70
            AND volume > 1.2x average.
    """
    NAME = "MomentumStrategy"
    VERSION = "1.1.0"
    CATEGORY = "momentum"
    TIMEFRAME = "daily"
    UNIVERSE = "nifty100"

    def __init__(self, momentum_period: int = 252, skip_period: int = 21,
                 ema_period: int = 50, rsi_period: int = 14, rsi_max: float = 70.0,
                 volume_ma_period: int = 20, volume_multiplier: float = 1.2,
                 **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.momentum_period = momentum_period
        self.skip_period = skip_period
        self.ema_period = ema_period
        self.rsi_period = rsi_period
        self.rsi_max = rsi_max
        self.volume_ma_period = volume_ma_period
        self.volume_multiplier = volume_multiplier
        self._warmup_period = momentum_period + 10

    def get_parameters(self) -> Dict[str, Any]:
        return {"momentum_period": self.momentum_period, "skip_period": self.skip_period,
                "ema_period": self.ema_period, "rsi_period": self.rsi_period,
                "rsi_max": self.rsi_max, "volume_ma_period": self.volume_ma_period,
                "volume_multiplier": self.volume_multiplier}

    def validate_parameters(self) -> bool:
        assert 60 <= self.momentum_period <= 504
        assert 1 <= self.skip_period <= 63
        assert 10 <= self.ema_period <= 200
        assert 7 <= self.rsi_period <= 28
        assert 60 <= self.rsi_max <= 90
        return True

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        close = data["Close"]
        volume = data.get("Volume", pd.Series(1, index=data.index))

        # 12-1 month momentum (skip last month to avoid reversal)
        long_return = close.shift(self.skip_period) / close.shift(self.momentum_period) - 1

        # EMA trend filter
        ema = close.ewm(span=self.ema_period, adjust=False).mean()
        above_ema = close > ema

        # RSI overbought filter
        delta = close.diff()
        avg_gain = delta.clip(lower=0).ewm(com=self.rsi_period-1, adjust=False).mean()
        avg_loss = (-delta.clip(upper=0)).ewm(com=self.rsi_period-1, adjust=False).mean()
        rsi = 100 - (100 / (1 + avg_gain / avg_loss.replace(0, np.nan)))
        not_overbought = rsi < self.rsi_max

        # Volume confirmation
        vol_ma = volume.rolling(self.volume_ma_period).mean()
        high_volume = volume > (vol_ma * self.volume_multiplier)

        # Entry: all conditions
        entry = (long_return > 0) & above_ema & not_overbought & high_volume
        # Exit: momentum negative or price breaks EMA
        exit_cond = (long_return <= 0) | ~above_ema

        signals = pd.Series(0, index=data.index, dtype=int)
        signals[entry] = 1
        signals[exit_cond & ~entry] = -1
        # CRITICAL: Shift to prevent look-ahead bias
        return signals.shift(1).fillna(0).astype(int)


@register_strategy
class MeanReversionStrategy(BaseStrategy):
    """Bollinger Band + RSI Mean Reversion."""
    NAME = "MeanReversionStrategy"
    VERSION = "1.0.0"
    CATEGORY = "mean_reversion"
    TIMEFRAME = "daily"
    UNIVERSE = "nifty50"

    def __init__(self, bb_period: int = 20, bb_std: float = 2.0,
                 rsi_oversold: float = 30.0, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.rsi_oversold = rsi_oversold
        self._warmup_period = bb_period + 10

    def get_parameters(self): return {"bb_period": self.bb_period, "bb_std": self.bb_std, "rsi_oversold": self.rsi_oversold}
    def validate_parameters(self):
        assert 10 <= self.bb_period <= 100; assert 1.0 <= self.bb_std <= 4.0; return True

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        close = data["Close"]
        sma = close.rolling(self.bb_period).mean()
        std = close.rolling(self.bb_period).std()
        lower = sma - std * self.bb_std
        delta = close.diff()
        avg_gain = delta.clip(lower=0).ewm(com=self.bb_period-1, adjust=False).mean()
        avg_loss = (-delta.clip(upper=0)).ewm(com=self.bb_period-1, adjust=False).mean()
        rsi = 100 - (100 / (1 + avg_gain / avg_loss.replace(0, np.nan)))
        entry = (close < lower) & (rsi < self.rsi_oversold)
        exit_cond = close >= sma
        signals = pd.Series(0, index=data.index, dtype=int)
        signals[entry] = 1
        signals[exit_cond & ~entry] = -1
        return signals.shift(1).fillna(0).astype(int)


@register_strategy
class BreakoutStrategy(BaseStrategy):
    """Donchian Channel Breakout with Volume Expansion."""
    NAME = "BreakoutStrategy"
    VERSION = "1.0.0"
    CATEGORY = "breakout"
    TIMEFRAME = "daily"
    UNIVERSE = "nifty100"

    def __init__(self, donchian_period: int = 55, volume_factor: float = 1.5,
                 atr_period: int = 14, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.donchian_period = donchian_period
        self.volume_factor = volume_factor
        self.atr_period = atr_period
        self._warmup_period = donchian_period + 10

    def get_parameters(self): return {"donchian_period": self.donchian_period, "volume_factor": self.volume_factor, "atr_period": self.atr_period}
    def validate_parameters(self):
        assert 20 <= self.donchian_period <= 200; assert 1.0 <= self.volume_factor <= 5.0; return True

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        close, high, low = data["Close"], data["High"], data["Low"]
        volume = data.get("Volume", pd.Series(1, index=data.index))
        channel_high = high.rolling(self.donchian_period).max()
        vol_avg = volume.rolling(20).mean()
        breakout_entry = (close >= channel_high.shift(1)) & (volume > vol_avg * self.volume_factor)
        exit_cond = close < low.rolling(20).min().shift(1)
        signals = pd.Series(0, index=data.index, dtype=int)
        signals[breakout_entry] = 1
        signals[exit_cond] = -1
        return signals.shift(1).fillna(0).astype(int)
