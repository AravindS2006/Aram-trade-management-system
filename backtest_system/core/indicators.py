import numpy as np
import pandas as pd


def sma(series: pd.Series, period: int) -> pd.Series:
    """
    Calculate Simple Moving Average (SMA).
    """
    return series.rolling(window=period).mean()

def ema(series: pd.Series, period: int) -> pd.Series:
    """
    Calculate Exponential Moving Average (EMA).
    """
    return series.ewm(span=period, adjust=False).mean()

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate Relative Strength Index (RSI).
    """
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ma_up = up.ewm(com=period-1, adjust=False).mean()
    ma_down = down.ewm(com=period-1, adjust=False).mean()
    rs = ma_up / ma_down
    return 100 - (100 / (1 + rs))

def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """
    Calculate Moving Average Convergence Divergence (MACD).
    Returns DataFrame with columns: ['macd_line', 'signal_line', 'histogram']
    """
    exp1 = ema(series, fast)
    exp2 = ema(series, slow)
    macd_line = exp1 - exp2
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return pd.DataFrame({
        'macd_line': macd_line,
        'signal_line': signal_line,
        'histogram': histogram
    })

def bollinger_bands(series: pd.Series, period: int = 20, std_dev: int = 2) -> pd.DataFrame:
    """
    Calculate Bollinger Bands.
    Returns DataFrame with columns: ['upper_band', 'middle_band', 'lower_band']
    """
    middle_band = sma(series, period)
    std = series.rolling(window=period).std()
    upper_band = middle_band + (std * std_dev)
    lower_band = middle_band - (std * std_dev)
    return pd.DataFrame({
        'upper_band': upper_band,
        'middle_band': middle_band,
        'lower_band': lower_band
    })

def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate Average True Range (ATR).
    """
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

def supertrend(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 7, multiplier: float = 3.0) -> pd.DataFrame:
    """
    Calculate Supertrend indicator.
    Returns DataFrame with columns: ['supertrend', 'direction']
    direction: 1 (uptrend), -1 (downtrend)
    """
    if len(high) == 0:
        return pd.DataFrame({'supertrend': [], 'direction': []})
        
    atr_val = atr(high, low, close, period)
    basic_upper = (high + low) / 2 + multiplier * atr_val
    basic_lower = (high + low) / 2 - multiplier * atr_val
    
    st = np.zeros(len(close))
    direction = np.zeros(len(close))
    
    # Initialize first values
    st[0] = basic_lower.iloc[0] if not np.isnan(basic_lower.iloc[0]) else 0
    direction[0] = 1
    
    # Loop implementation due to recursive nature of Supertrend
    # Note: Can be optimized with numba for very large datasets, but using python loop for clarity/pandas compatibility
    for i in range(1, len(close)):
        # Calculate Upper Band
        if basic_upper.iloc[i] < st[i-1] or close.iloc[i-1] > st[i-1]:
            curr_upper = basic_upper.iloc[i]
        else:
            curr_upper = st[i-1]
            
        # Calculate Lower Band
        if basic_lower.iloc[i] > st[i-1] or close.iloc[i-1] < st[i-1]:
            curr_lower = basic_lower.iloc[i]
        else:
            curr_lower = st[i-1]
            
        # Determine Trend
        if st[i-1] == curr_upper: # Previous was broken upper / downtrend
            if close.iloc[i] > curr_upper:
                direction[i] = 1 # Trend reversal up
                st[i] = curr_lower
            else:
                direction[i] = -1 # Continuation down
                st[i] = curr_upper
        else: # Previous was broken lower / uptrend
            if close.iloc[i] < curr_lower:
                direction[i] = -1 # Trend reversal down
                st[i] = curr_upper
            else:
                direction[i] = 1 # Continuation up
                st[i] = curr_lower
                
    return pd.DataFrame({
        'supertrend': st,
        'direction': direction
    }, index=close.index)

def vwap(df: pd.DataFrame) -> pd.Series:
    q = df['Volume']
    p = (df['High'] + df['Low'] + df['Close']) / 3
    # Group by trading day
    return (p * q).groupby(df.index.date).cumsum() / q.groupby(df.index.date).cumsum()
