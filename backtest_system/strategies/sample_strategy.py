from core.indicators import rsi, vwap
from core.strategy import BaseStrategy


def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

class VWAPCrossStrategy(BaseStrategy):
    """
    Improved Strategy:
    Buys when Price crosses above VWAP, RSI is rebounding (> 40) and short EMA > long EMA (Trend is up).
    Sells when Price crosses below VWAP, RSI is dropping (< 60) and short EMA < long EMA (Trend is down).
    Also includes a basic volume filter.
    """
    def generate_indicators(self):
        rsi_period = self.params.get('rsi_period', 14)
        ema_short = self.params.get('ema_short', 9)
        ema_long = self.params.get('ema_long', 21)
        
        self.data['VWAP'] = vwap(self.data)
        self.data['RSI'] = rsi(self.data['Close'], period=rsi_period)
        self.data['EMA_Short'] = ema(self.data['Close'], period=ema_short)
        self.data['EMA_Long'] = ema(self.data['Close'], period=ema_long)
        
        # Simple volume moving average as a filter
        self.data['Vol_MA'] = self.data['Volume'].rolling(window=20).mean()
        
    def generate_signals(self):
        c = self.data['Close']
        v = self.data['VWAP']
        rsi_val = self.data['RSI']
        ema_s = self.data['EMA_Short']
        ema_l = self.data['EMA_Long']
        vol = self.data['Volume']
        vol_ma = self.data['Vol_MA']
        
        # Buy: Price crosses VWAP up, trend is EMA short > EMA long, adequate volume, RSI not overbought
        buy_cond = (
            (c > v) & (c.shift(1) <= v.shift(1)) & 
            (ema_s > ema_l) & 
            (rsi_val > 40) & (rsi_val < 70) & 
            (vol > vol_ma * 0.8) # Volume must be at least 80% of average
        )
        
        # Sell: Price crosses VWAP down, trend is EMA short < EMA long, adequate volume, RSI not oversold
        sell_cond = (
            (c < v) & (c.shift(1) >= v.shift(1)) & 
            (ema_s < ema_l) & 
            (rsi_val < 60) & (rsi_val > 30) &
            (vol > vol_ma * 0.8)
        )
        
        self.signals.loc[buy_cond, 'signal'] = 1
        self.signals.loc[sell_cond, 'signal'] = -1
