from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
import pytz

from strategies.ichimoku_strategy.utils.time_filter import is_valid_session

IST = pytz.timezone("Asia/Kolkata")


def _parse_timeframe_minutes(timeframe: str) -> int:
    """Parse timeframe string like '1m' or '5m' into minutes."""
    tf = timeframe.strip().lower()
    if not tf.endswith("m"):
        raise ValueError("Only minute-based timeframes are supported for gap validation.")
    return int(tf[:-1])


def _to_ist_index(df: pd.DataFrame) -> pd.DataFrame:
    """Convert index to IST and sort ascending."""
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC").tz_convert(IST)
    else:
        df.index = df.index.tz_convert(IST)
    return df.sort_index()


def _validate_no_large_gaps(df: pd.DataFrame, timeframe_minutes: int) -> None:
    """Assert no gaps larger than timeframe during active session windows."""
    if df.empty:
        return

    idx = pd.DatetimeIndex([ts for ts in df.index if is_valid_session(ts)])
    if len(idx) < 2:
        return

    diffs = idx.to_series().diff().dropna()
    max_gap = diffs.max()
    allowed = pd.Timedelta(minutes=timeframe_minutes)
    if pd.notna(max_gap) and max_gap > allowed:
        raise AssertionError(f"Detected session gap {max_gap} > timeframe {allowed}")


def fetch_ohlcv(
    symbol: str,
    timeframe: str,
    start: datetime,
    end: datetime,
    source: str = "zerodha",
) -> pd.DataFrame:
    """Fetch OHLCV candles with IST-aware index and standardized schema."""
    if source == "csv":
        csv_path = Path("data/historical") / f"{symbol}_{timeframe}.csv"
        out = pd.read_csv(csv_path, index_col=0, parse_dates=True)
    elif source == "zerodha":
        raise NotImplementedError("Connect Kite API — see https://kite.trade/docs")
    else:
        raise ValueError("source must be either 'csv' or 'zerodha'")

    if isinstance(out.columns, pd.MultiIndex):
        out.columns = out.columns.droplevel(1)

    rename_map = {
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume",
    }
    out = out.rename(columns=rename_map)
    out = out[["open", "high", "low", "close", "volume"]].copy()

    mask = (out.index >= pd.Timestamp(start)) & (out.index <= pd.Timestamp(end))
    out = out.loc[mask]

    out = _to_ist_index(out)
    out = out[out["volume"] > 0]
    out = out.dropna().astype(float)
    _validate_no_large_gaps(out, _parse_timeframe_minutes(timeframe))
    return out

