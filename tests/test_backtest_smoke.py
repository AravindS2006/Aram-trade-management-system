import numpy as np
import pandas as pd

from core.backtester import IntradayBacktester
from strategies.intraday_momentum_strategy import IntradayMomentumStrategy


def _sample_ohlcv(rows: int = 250) -> pd.DataFrame:
    index = pd.date_range("2024-01-01 09:15:00", periods=rows, freq="min")
    base = np.linspace(100.0, 105.0, rows)
    close = base + 0.15 * np.sin(np.linspace(0.0, 8.0, rows))
    open_ = np.roll(close, 1)
    open_[0] = close[0]
    high = np.maximum(open_, close) + 0.2
    low = np.minimum(open_, close) - 0.2
    volume = np.linspace(1_000, 3_000, rows)

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


def test_intraday_backtest_smoke() -> None:
    df = _sample_ohlcv()

    strategy = IntradayMomentumStrategy(
        df,
        params={
            "supertrend_period": 10,
            "supertrend_multiplier": 3.0,
            "rsi_period": 14,
            "ema_period": 9,
        },
    )

    data_with_signals = strategy.get_data_with_signals()
    backtester = IntradayBacktester(data_with_signals, initial_capital=100000)
    tearsheet, metrics = backtester.run()

    assert isinstance(metrics, dict)

    if tearsheet is not None:
        assert not tearsheet.empty
        assert "Net PnL" in tearsheet.columns
        assert "Equity" in tearsheet.columns

    assert "Total Trades" in metrics
    assert "Final Equity" in metrics
