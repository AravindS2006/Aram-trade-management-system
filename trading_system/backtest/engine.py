from __future__ import annotations

import pandas as pd

from core.backtester import IntradayBacktester


def run_backtest(data_with_signals: pd.DataFrame, **kwargs):
    """Compatibility wrapper around the current IntradayBacktester."""
    return IntradayBacktester(data_with_signals, **kwargs).run()
