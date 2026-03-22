"""
Strategy Development Template
Use this template to quickly start developing a new strategy.

Development Checklist:
- [ ] Strategy inherits from `Strategy` base class
- [ ] `generate_signals()` returns np.array with values in {-1, 0, 1}
- [ ] Handled edge cases (empty data, NaNs, insufficient lookback)
- [ ] Used vectorized operations (no loops over data)
- [ ] Added docstrings to all methods
- [ ] Tested with sample data locally
- [ ] Backtested on full RELIANCE dataset
- [ ] Metrics look reasonable (not >5 Sharpe ratio)
- [ ] Documented expected performance

Advanced Patterns:
1. Multi-Position Strategy
    self.positions = {}
    signal = 1 if buy_condition else (-1 if sell_condition else 0)

2. Variable Position Sizing
    volatility = data['close'].rolling(20).std()
    size = 100 / (1 + volatility.iloc[i])

3. Time-Based Filters
    hour = pd.Timestamp(timestamp).hour
    if 9 <= hour <= 14:  # Only trade 9:30 AM - 2:30 PM
        signal = generate_signal()
"""

import numpy as np
import pandas as pd

class Strategy:
    pass

class MyStrategy(Strategy):
    """
    [DESCRIPTION]: Brief description of the strategy logic.

    Example: "Uses two moving averages (fast/slow) to generate buy/sell signals.
    Buys when fast MA crosses above slow MA, sells on crossover."

    Parameters:
        fast_period: Length of fast moving average
        slow_period: Length of slow moving average

    Expected Return: ~10-20% annually on RELIANCE data
    """

    def __init__(self, fast_period: int = 20, slow_period: int = 50):
        super().__init__()
        self.fast_period = fast_period
        self.slow_period = slow_period

        # Initialize state trackers
        self.prev_fast = None
        self.prev_slow = None

    def generate_signals(self, data: pd.DataFrame) -> np.ndarray:
        """
        Generate trading signals based on strategy logic.

        Args:
            data: DataFrame with columns [open, high, low, close, volume]       
                  Index is timestamps in chronological order

        Returns:
            np.array of shape (len(data),) with values:
                +1: BUY signal
                -1: SELL signal
                 0: HOLD (no action)

        Notes:
            - Use vectorized operations (avoid loops)
            - Pre-calculate expensive indicators
            - Handle edge cases (empty data, first few bars, gaps)
        """
        signals = np.zeros(len(data))

        # Calculate indicators
        fast_ma = data['close'].rolling(window=self.fast_period).mean()
        slow_ma = data['close'].rolling(window=self.slow_period).mean()

        # Generate signals
        # Avoid first slow_period bars (insufficient data for calculation)      
        for i in range(self.slow_period, len(data)):
            # Crossover: fast MA crosses above slow MA -> BUY
            if fast_ma.iloc[i] > slow_ma.iloc[i] and \
               fast_ma.iloc[i-1] <= slow_ma.iloc[i-1]:
                signals[i] = 1

            # Crossunder: fast MA crosses below slow MA -> SELL
            elif fast_ma.iloc[i] < slow_ma.iloc[i] and \
                 fast_ma.iloc[i-1] >= slow_ma.iloc[i-1]:
                signals[i] = -1

        return signals

    def on_signal(self, signal: int, price: float) -> None:
        """
        Execute trades based on generated signals.
        Optional: override for custom trade execution logic.

        Args:
            signal: Generated signal (+1, -1, or 0)
            price: Current price at signal time

        Example use cases:
            - Add trailing stops
            - Position sizing based on volatility
            - Skip trades under certain conditions
        """
        # Default behavior: let backtester handle all trades
        # Override this method if custom execution needed
        pass


# ============================================================================  
# TESTING
# ============================================================================  

if __name__ == "__main__":
    pass