from __future__ import annotations

import pandas as pd


def calculate_vwap(df: pd.DataFrame) -> pd.DataFrame:
    from strategies.ichimoku_strategy.data.preprocessor import preprocess

    return preprocess(df)

