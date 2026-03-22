import numpy as np
import pandas as pd

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
