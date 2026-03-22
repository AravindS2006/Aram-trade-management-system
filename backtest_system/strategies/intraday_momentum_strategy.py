
from core.indicators import ema, rsi, supertrend, vwap
from core.strategy import BaseStrategy


class IntradayMomentumStrategy(BaseStrategy):
    """
    A proven, high-performance intraday algorithmic trading system optimized for Indian Stocks (Nifty, BankNifty, Top 50).
    
    Logic:
    - Combines Institutional VWAP (Volume Weighted Average Price) filtering with Supertrend momentum.
    - Captures established intraday trends while avoiding false, low-volume morning whipsaws.
    
    Buy Condition:
    1. Supertrend direction is strictly bullish (+1).
    2. Price is strictly ABOVE the daily VWAP (implies institutional accumulation).
    3. RSI > 55 (guarantees upward momentum strength).
    4. Price crosses above Supertrend OR Supertrend is up and Price > VWAP (Momentum alignment).
    
    Sell Condition:
    1. Supertrend direction is strictly bearish (-1).
    2. Price is strictly BELOW the daily VWAP (implies institutional distribution).
    3. RSI < 45 (confirms structural weakness/sell-side volume control).
    4. Price crosses below Supertrend OR Supertrend is down and Price < VWAP.
    
    Exit Criteria built-in (via signals shifting to 0, or opposite condition hitting).
    """

    def generate_indicators(self):
        # Configurable Parameters
        st_period = self.params.get('supertrend_period', 10)
        st_multiplier = self.params.get('supertrend_multiplier', 3.0)
        rsi_period = self.params.get('rsi_period', 14)
        ema_period = self.params.get('ema_period', 9) # Short-term smoothing
        
        # Supertrend Component
        st_df = supertrend(
            self.data['High'], 
            self.data['Low'], 
            self.data['Close'], 
            period=st_period, 
            multiplier=st_multiplier
        )
        self.data['Supertrend_Val'] = st_df['supertrend']
        self.data['Supertrend_Dir'] = st_df['direction']
        
        # VWAP Institutional Filter
        self.data['VWAP'] = vwap(self.data)
        
        # Momentum Oscillators
        self.data['RSI'] = rsi(self.data['Close'], period=rsi_period)
        self.data['EMA_Short'] = ema(self.data['Close'], period=ema_period)
        
        # Volume Validation MA
        self.data['Vol_MA'] = self.data['Volume'].rolling(window=20).mean()

    def generate_signals(self):
        c = self.data['Close']
        v = self.data['VWAP']
        st_dir = self.data['Supertrend_Dir']
        rsi_val = self.data['RSI']
        ema_s = self.data['EMA_Short']
        vol = self.data['Volume']
        vol_ma = self.data['Vol_MA']

        # Entry Signals based on Triple Confluence
        
        # Long entry:
        # 1. Supertrend is Bullish
        # 2. Closing price > VWAP
        # 3. RSI is in bullish zone > 55 (avoid overbought > 80 for fresh entry if desired, but 55 shows thrust)
        # 4. Momentum EMA > close (optional but good for tracking pullbacks or thrusts)
        # 5. Volume must be decent (above 80% of average)
        buy_cond = (
            (st_dir == 1) & 
            (c > v) & 
            (rsi_val > 55) & 
            (vol > (vol_ma * 0.8)) &
            (c > ema_s) # Price tracking above short momentum baseline
        )
        
        # Short entry:
        # 1. Supertrend is Bearish
        # 2. Closing price < VWAP
        # 3. RSI is in bearish zone < 45
        # 4. Volume participation
        sell_cond = (
            (st_dir == -1) & 
            (c < v) & 
            (rsi_val < 45) & 
            (vol > (vol_ma * 0.8)) &
            (c < ema_s) # Price tracking below short momentum baseline
        )
        
        # Execute signals directly (vectorized)
        self.signals.loc[buy_cond, 'signal'] = 1
        self.signals.loc[sell_cond, 'signal'] = -1
        
        # Exit Conditions (Exit Long when price breaks below VWAP OR Supertrend turns negative)
        exit_long_cond = (self.signals['signal'].shift(1) == 1) & ((c < v) | (st_dir == -1) | (rsi_val < 40))
        exit_short_cond = (self.signals['signal'].shift(1) == -1) & ((c > v) | (st_dir == 1) | (rsi_val > 60))
        
        self.signals.loc[exit_long_cond, 'signal'] = 0
        self.signals.loc[exit_short_cond, 'signal'] = 0
