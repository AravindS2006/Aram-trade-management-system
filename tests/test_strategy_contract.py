import numpy as np
import pandas as pd
import pytz

from strategies.eorb_strategy import EORBStrategy
from strategies.ichimoku_strategy import IchimokuRSIVWAPStrategy
from strategies.intraday_momentum_strategy import IntradayMomentumStrategy
from strategies.sample_strategy import VWAPCrossStrategy

REQUIRED_SIGNALS = {-1, 0, 1}


def _load_df():
    rows = 250
    index = pd.date_range("2024-01-01 09:15:00", periods=rows, freq="min")
    base = np.linspace(120.0, 125.0, rows)
    close = base + 0.2 * np.sin(np.linspace(0.0, 10.0, rows))
    open_ = np.roll(close, 1)
    open_[0] = close[0]
    high = np.maximum(open_, close) + 0.25
    low = np.minimum(open_, close) - 0.25
    volume = np.linspace(1_500, 3_500, rows)

    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": volume,
        },
        index=index,
    )


def _load_eorb_df():
    """Generate multi-session 5-min OHLCV data with IST timezone for E-ORB testing."""
    ist = pytz.timezone("Asia/Kolkata")
    # Create 3 trading days of 5-min bars (9:15 to 15:30 = 75 bars per day)
    sessions = []
    for day_offset in range(3):
        day_start = pd.Timestamp(f"2024-01-{2 + day_offset} 09:15:00", tz=ist)
        bars = pd.date_range(day_start, periods=75, freq="5min")
        sessions.append(bars)
    index = sessions[0].append(sessions[1]).append(sessions[2])  # type: ignore[union-attr]

    rows = len(index)
    base = np.linspace(2400.0, 2450.0, rows)
    close = base + 5.0 * np.sin(np.linspace(0.0, 15.0, rows))
    open_ = np.roll(close, 1)
    open_[0] = close[0]
    high = np.maximum(open_, close) + 3.0
    low = np.minimum(open_, close) - 3.0
    volume = np.linspace(50_000, 200_000, rows)

    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": volume,
        },
        index=index,
    )


def test_intraday_strategy_signal_contract() -> None:
    df = _load_df()
    strategy = IntradayMomentumStrategy(df)
    out = strategy.get_data_with_signals()

    assert "signal" in out.columns
    assert set(out["signal"].dropna().astype(int).unique()).issubset(REQUIRED_SIGNALS)


def test_vwap_strategy_signal_contract() -> None:
    df = _load_df()
    strategy = VWAPCrossStrategy(df)
    out = strategy.get_data_with_signals()

    assert "signal" in out.columns
    assert set(out["signal"].dropna().astype(int).unique()).issubset(REQUIRED_SIGNALS)


def test_ichimoku_strategy_signal_contract() -> None:
    df = _load_df()
    strategy = IchimokuRSIVWAPStrategy(df)
    out = strategy.get_data_with_signals()

    assert "signal" in out.columns
    assert set(out["signal"].dropna().astype(int).unique()).issubset(REQUIRED_SIGNALS)


def test_eorb_strategy_signal_contract() -> None:
    df = _load_eorb_df()
    strategy = EORBStrategy(
        df,
        params={
            "min_signal_score": 5,
            "cooldown_bars": 3,
            "max_daily_trades": 3,
            "allow_short": True,
            "vix_today": 14.5,
        },
    )
    out = strategy.get_data_with_signals()

    assert "signal" in out.columns
    assert set(out["signal"].dropna().astype(int).unique()).issubset(REQUIRED_SIGNALS)

