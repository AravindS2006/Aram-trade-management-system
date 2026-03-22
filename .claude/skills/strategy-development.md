# Skill: Strategy Development — Aram-TMS

## Strategy Template
```python
from src.strategies.base_strategy import BaseStrategy, register_strategy

@register_strategy
class MyStrategy(BaseStrategy):
    NAME = "MyStrategy"
    VERSION = "1.0.0"
    CATEGORY = "momentum"   # momentum|mean_reversion|breakout|ml|factor
    TIMEFRAME = "daily"
    UNIVERSE = "nifty50"

    def __init__(self, lookback: int = 20, threshold: float = 0.02, **kwargs):
        super().__init__(**kwargs)
        self.lookback = lookback
        self.threshold = threshold

    def get_parameters(self):
        return {"lookback": self.lookback, "threshold": self.threshold}

    def validate_parameters(self):
        assert 5 <= self.lookback <= 200
        assert 0.001 <= self.threshold <= 0.1
        return True

    def generate_signals(self, data):
        """
        Args: data — DataFrame with Open, High, Low, Close, Volume (DatetimeIndex)
        Returns: Series of 1 (buy), -1 (sell), 0 (hold) — same index as data
        CRITICAL: Always shift(1) to prevent look-ahead bias.
        """
        close = data["Close"]
        sma = close.rolling(self.lookback).mean()
        signals = pd.Series(0, index=data.index, dtype=int)
        signals[close > sma * (1 + self.threshold)] = 1
        signals[close < sma * (1 - self.threshold)] = -1
        return signals.shift(1).fillna(0).astype(int)  # ALWAYS shift!
```
