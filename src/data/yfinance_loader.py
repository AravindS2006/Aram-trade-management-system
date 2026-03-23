"""
YFinance Data Loader - Aram-TMS
Short-term market data (<2 years) with parquet caching and validation.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf
from loguru import logger

from src.data.validators import validate_ohlcv

NSE_HOLIDAYS = {
    "2024-01-26",
    "2024-03-25",
    "2024-03-29",
    "2024-04-14",
    "2024-04-17",
    "2024-04-21",
    "2024-05-23",
    "2024-06-17",
    "2024-07-17",
    "2024-08-15",
    "2024-10-02",
    "2024-10-14",
    "2024-11-01",
    "2024-11-15",
    "2024-12-25",
    "2025-01-26",
    "2025-02-26",
    "2025-03-14",
    "2025-03-31",
    "2025-04-10",
    "2025-04-14",
    "2025-04-18",
    "2025-05-01",
    "2025-08-15",
    "2025-10-02",
    "2025-10-21",
    "2025-11-05",
    "2025-12-25",
}
VALID_INTERVALS = ["1m", "2m", "5m", "15m", "30m", "60m", "1h", "1d", "1wk", "1mo"]


class YFinanceLoader:
    """Fetch and cache NSE/BSE market data from Yahoo Finance."""

    def __init__(self, cache_dir: str | Path = "data/cache", auto_adjust: bool = True) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.auto_adjust = auto_adjust

    def fetch(
        self,
        symbol: str,
        start: str,
        end: str | None = None,
        interval: str = "1d",
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """Fetch OHLCV for one symbol. Symbol: RELIANCE.NS or RELIANCE (auto .NS added)."""
        if interval not in VALID_INTERVALS:
            raise ValueError(f"Invalid interval: {interval}")
        formatted = self._fmt(symbol)
        end = end or datetime.today().strftime("%Y-%m-%d")
        if use_cache:
            cached = self._load_cache(formatted, interval, start, end)
            if cached is not None:
                return cached
        data = self._download(formatted, start, end, interval)
        if data.empty:
            logger.warning(f"No data: {formatted}")
            return pd.DataFrame()
        data = self._clean(data, symbol)
        if use_cache and interval == "1d" and not data.empty:
            self._save_cache(data, formatted, interval)
        return data

    def fetch_universe(
        self,
        symbols: list[str],
        start: str,
        end: str | None = None,
        interval: str = "1d",
        use_cache: bool = True,
    ) -> dict[str, pd.DataFrame]:
        """Batch-download multiple symbols efficiently."""
        end = end or datetime.today().strftime("%Y-%m-%d")
        result: dict[str, pd.DataFrame] = {}
        to_download = []
        for sym in symbols:
            fmt = self._fmt(sym)
            if use_cache:
                cached = self._load_cache(fmt, interval, start, end)
                if cached is not None:
                    result[sym.replace(".NS", "").replace(".BO", "")] = cached
                    continue
            to_download.append((sym, fmt))
        for i in range(0, len(to_download), 50):
            batch = to_download[i : i + 50]
            try:
                tickers = [b[1] for b in batch]
                raw = yf.download(
                    tickers,
                    start=start,
                    end=end,
                    interval=interval,
                    auto_adjust=self.auto_adjust,
                    group_by="ticker",
                    progress=False,
                    threads=True,
                )
                for orig, fmt in batch:
                    clean = orig.replace(".NS", "").replace(".BO", "")
                    try:
                        sym_data = raw[fmt] if len(batch) > 1 else raw
                        if not sym_data.empty:
                            cleaned = self._clean(sym_data, fmt)
                            result[clean] = cleaned
                    except (KeyError, TypeError):
                        pass
            except Exception as e:
                logger.error(f"Batch download error: {e}")
            if i + 50 < len(to_download):
                time.sleep(0.5)
        logger.info(f"Loaded {len(result)}/{len(symbols)} symbols")
        return result

    def fetch_index(
        self,
        index_name: str = "NIFTY50",
        start: str = "2020-01-01",
        end: str | None = None,
        interval: str = "1d",
    ) -> pd.DataFrame:
        INDEX_MAP = {
            "NIFTY50": "^NSEI",
            "NIFTYBANK": "^NSEBANK",
            "SENSEX": "^BSESN",
            "NIFTYIT": "^CNXIT",
        }
        ticker = INDEX_MAP.get(index_name.upper(), index_name)
        return self.fetch(ticker, start=start, end=end, interval=interval)

    def get_nifty50_symbols(self) -> list[str]:
        return [
            "RELIANCE.NS",
            "TCS.NS",
            "HDFCBANK.NS",
            "INFY.NS",
            "HINDUNILVR.NS",
            "ICICIBANK.NS",
            "KOTAKBANK.NS",
            "LT.NS",
            "SBIN.NS",
            "BHARTIARTL.NS",
            "AXISBANK.NS",
            "ITC.NS",
            "ASIANPAINT.NS",
            "MARUTI.NS",
            "HCLTECH.NS",
            "SUNPHARMA.NS",
            "TITAN.NS",
            "ULTRACEMCO.NS",
            "WIPRO.NS",
            "NESTLEIND.NS",
            "BAJFINANCE.NS",
            "POWERGRID.NS",
            "NTPC.NS",
            "TATAMOTORS.NS",
            "M&M.NS",
            "TECHM.NS",
            "ADANIPORTS.NS",
            "ONGC.NS",
            "COALINDIA.NS",
            "JSWSTEEL.NS",
            "TATASTEEL.NS",
            "HINDALCO.NS",
            "BPCL.NS",
            "GRASIM.NS",
            "DIVISLAB.NS",
            "BAJAJFINSV.NS",
            "CIPLA.NS",
            "DRREDDY.NS",
            "EICHERMOT.NS",
            "HEROMOTOCO.NS",
            "APOLLOHOSP.NS",
            "ADANIENT.NS",
            "TATACONSUM.NS",
            "BRITANNIA.NS",
            "SBILIFE.NS",
            "HDFCLIFE.NS",
            "UPL.NS",
            "INDUSINDBK.NS",
            "BAJAJ-AUTO.NS",
            "LTI.NS",
        ]

    def _fmt(self, symbol: str) -> str:
        if symbol.startswith("^"):
            return symbol
        if "." in symbol:
            return symbol
        return f"{symbol}.NS"

    def _download(self, symbol: str, start: str, end: str, interval: str) -> pd.DataFrame:
        for attempt in range(3):
            try:
                ticker = yf.Ticker(symbol)
                data = ticker.history(
                    start=start, end=end, interval=interval, auto_adjust=self.auto_adjust
                )
                if not data.empty:
                    return data
            except Exception as e:
                logger.warning(f"Download attempt {attempt + 1} failed: {e}")
                time.sleep(2**attempt)
        return pd.DataFrame()

    def _clean(self, data: pd.DataFrame, symbol: str) -> pd.DataFrame:
        if data.empty:
            return data
        if isinstance(data.columns, pd.MultiIndex):
            data = data.copy()
            data.columns = [str(c[-1]) for c in data.columns]
        else:
            normalized_cols = []
            for c in data.columns:
                if isinstance(c, tuple):
                    parts = [str(p) for p in c if p not in (None, "")]
                    normalized_cols.append(parts[-1] if parts else "")
                else:
                    normalized_cols.append(str(c))
            data = data.copy()
            data.columns = normalized_cols

        data = data.rename(columns={c: c.title() for c in data.columns})
        required = ["Open", "High", "Low", "Close", "Volume"]
        for col in required:
            if col not in data.columns:
                data[col] = 0 if col == "Volume" else np.nan
        data = data[required].copy()
        if hasattr(data.index, "tz") and data.index.tz is not None:
            data.index = data.index.tz_convert("Asia/Kolkata").tz_localize(None)
        data = data[data.index.dayofweek < 5]
        for col in ["Open", "High", "Low", "Close"]:
            data[col] = pd.to_numeric(data[col], errors="coerce")
        data["Volume"] = pd.to_numeric(data["Volume"], errors="coerce").fillna(0)
        data = data[(data["Close"] > 0) & (data["High"] >= data["Low"])]
        pct = data["Close"].pct_change().abs()
        data = data[pct < 0.5]
        data = data.ffill(limit=3).dropna(subset=["Close"]).sort_index()
        data = data[~data.index.duplicated(keep="last")]
        validation = validate_ohlcv(data)
        if not validation.valid:
            logger.warning(f"Validation issues for {symbol}: {validation.errors}")
        return data

    def _cache_path(self, symbol: str, interval: str) -> Path:
        safe = symbol.replace("^", "IDX_").replace(".", "_")
        return self.cache_dir / f"{safe}_{interval}.parquet"

    def _load_cache(self, symbol: str, interval: str, start: str, end: str) -> pd.DataFrame | None:
        p = self._cache_path(symbol, interval)
        if not p.exists():
            return None
        try:
            cached = pd.read_parquet(p)
            if cached.empty:
                return None
            if cached.index[0].date() <= pd.Timestamp(start).date() and cached.index[
                -1
            ].date() >= pd.Timestamp(end).date() - timedelta(days=5):
                return cached[start:end]
        except Exception:
            pass
        return None

    def _save_cache(self, data: pd.DataFrame, symbol: str, interval: str) -> None:
        p = self._cache_path(symbol, interval)
        try:
            if p.exists():
                existing = pd.read_parquet(p)
                data = pd.concat([existing, data]).sort_index()
                data = data[~data.index.duplicated(keep="last")]
            data.to_parquet(p, compression="snappy")
        except Exception as e:
            logger.warning(f"Cache write failed: {e}")
