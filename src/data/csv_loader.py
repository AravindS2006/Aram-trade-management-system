"""
Kaggle CSV Data Loader - Aram-TMS
Loads long-term historical NSE/BSE data from downloaded Kaggle CSV files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger

from src.data.validators import validate_ohlcv

COLUMN_ALIASES = {
    "open": ["Open", "OPEN", "open", "Open Price"],
    "high": ["High", "HIGH", "high", "High Price"],
    "low": ["Low", "LOW", "low", "Low Price"],
    "close": ["Close", "CLOSE", "close", "Close Price", "Last", "LTP"],
    "volume": ["Volume", "VOLUME", "volume", "Vol", "No of Shares"],
    "date": ["Date", "DATE", "date", "Datetime", "timestamp", "Time", "TIMESTAMP"],
}


class KaggleCSVLoader:
    """
    Loads long-term historical market data from Kaggle CSV files.

    Expected file location: data/raw/csv/
    Naming: RELIANCE.csv | RELIANCE_NSE.csv | RELIANCE_daily.csv
    Required columns: Date, Open, High, Low, Close, Volume (names flexible)
    """

    def __init__(
        self, data_dir: str | Path = "data/raw/csv", processed_dir: str | Path = "data/processed"
    ) -> None:
        self.data_dir = Path(data_dir)
        self.processed_dir = Path(processed_dir)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        if self.data_dir.exists():
            n = len(list(self.data_dir.glob("*.csv")))
            logger.info(f"KaggleCSVLoader: {n} CSV files in {self.data_dir}")
        else:
            logger.warning(f"CSV dir not found: {self.data_dir}")

    def load(
        self,
        symbol: str,
        start: str | None = None,
        end: str | None = None,
        use_cache: bool = True,
        interval: str = "1d",
    ) -> pd.DataFrame:
        """Load data for a symbol from CSV. Caches to parquet for speed."""
        if use_cache:
            cached = self._load_parquet(symbol)
            if cached is not None:
                filtered = self._filter(cached, start, end)
                if filtered.empty:
                    meta = self.inspect_symbol(symbol)
                    raise ValueError(
                        f"No rows for {symbol} in requested range {start}..{end}. "
                        f"Available range: {meta.get('start')}..{meta.get('end')}"
                    )
                return self._to_interval(filtered, interval)
        csv_path = self._find_csv(symbol)
        if csv_path is None:
            raise FileNotFoundError(
                f"No CSV for '{symbol}' in {self.data_dir}. "
                f"Available: {self.list_available_symbols()[:10]}"
            )
        data = self._read_csv(csv_path, symbol)
        if use_cache and not data.empty:
            self._save_parquet(data, symbol)
        filtered = self._filter(data, start, end)
        if filtered.empty:
            meta = self.inspect_symbol(symbol)
            raise ValueError(
                f"No rows for {symbol} in requested range {start}..{end}. "
                f"Available range: {meta.get('start')}..{meta.get('end')}"
            )
        return self._to_interval(filtered, interval)

    def inspect_symbol(self, symbol: str) -> dict[str, Any]:
        """Return lightweight metadata for diagnostics without raising hard errors."""
        csv_path = self._find_csv(symbol)
        if csv_path is None:
            return {
                "exists": False,
                "path": None,
                "start": None,
                "end": None,
                "rows": 0,
                "columns": [],
            }
        try:
            raw = pd.read_csv(csv_path, nrows=5)
            cols = list(raw.columns)
            full = self._read_csv(csv_path, symbol)
            return {
                "exists": True,
                "path": str(csv_path),
                "start": str(full.index.min()) if not full.empty else None,
                "end": str(full.index.max()) if not full.empty else None,
                "rows": int(len(full)),
                "columns": cols,
            }
        except Exception:
            return {
                "exists": True,
                "path": str(csv_path),
                "start": None,
                "end": None,
                "rows": 0,
                "columns": [],
            }

    def load_all_available(
        self, start: str | None = None, end: str | None = None
    ) -> dict[str, pd.DataFrame]:
        result = {}
        for sym in self.list_available_symbols():
            try:
                data = self.load(sym, start=start, end=end)
                if not data.empty:
                    result[sym] = data
            except Exception as e:
                logger.warning(f"Failed to load {sym}: {e}")
        logger.info(f"Loaded {len(result)} symbols from CSV")
        return result

    def list_available_symbols(self) -> list[str]:
        if not self.data_dir.exists():
            return []
        syms = []
        for f in sorted(self.data_dir.glob("*.csv")):
            name = f.stem.upper()
            for suf in ["_NSE", "_BSE", "_DAILY", "_1D", "_EOD"]:
                name = name.replace(suf, "")
            syms.append(name)
        return syms

    def describe_dataset(self) -> pd.DataFrame:
        rows = []
        for sym in self.list_available_symbols():
            try:
                p = self._find_csv(sym)
                if p:
                    df = self.load(sym)
                    rows.append(
                        {
                            "Symbol": sym,
                            "File": p.name,
                            "Size_MB": round(p.stat().st_size / 1e6, 2),
                            "Start": df.index[0].date() if not df.empty else None,
                            "End": df.index[-1].date() if not df.empty else None,
                            "Bars": len(df),
                        }
                    )
            except Exception:
                pass
        return pd.DataFrame(rows)

    def _find_csv(self, symbol: str) -> Path | None:
        sym = symbol.upper().replace(".NS", "").replace(".BO", "")
        for pat in [
            f"{sym}.csv",
            f"{sym}_NSE.csv",
            f"{sym}_daily.csv",
            f"{sym}_EOD.csv",
            f"{sym.lower()}.csv",
        ]:
            p = self.data_dir / pat
            if p.exists():
                return p
        for f in self.data_dir.glob("*.csv"):
            if f.stem.upper().startswith(sym):
                return f
        return None

    def _read_csv(self, path: Path, symbol: str) -> pd.DataFrame:
        df = pd.read_csv(path, low_memory=False)
        date_col = self._find_col(df, "date")
        if date_col is None:
            raise ValueError(f"No date column in {path}. Cols: {list(df.columns)}")
        df = df.rename(columns={date_col: "Date"})
        parsed = pd.to_datetime(df["Date"], errors="coerce", format="mixed", dayfirst=False)
        if parsed.isna().mean() > 0.2:
            parsed = pd.to_datetime(df["Date"], errors="coerce", format="mixed", dayfirst=True)
        df["Date"] = parsed
        df = df.dropna(subset=["Date"])
        df = df.set_index("Date").sort_index()
        if hasattr(df.index, "tz") and df.index.tz:
            df.index = df.index.tz_localize(None)
        renames = {}
        for target in ["open", "high", "low", "close", "volume"]:
            col = self._find_col(df, target)
            if col:
                renames[col] = target.title()
            elif target == "volume":
                df["Volume"] = 0
        df = df.rename(columns=renames)
        avail = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
        df = df[avail].copy()
        for col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", ""), errors="coerce")
        df = df[df.index.dayofweek < 5]
        df = df[df["Close"] > 0].dropna(subset=["Close"])
        if "High" in df.columns and "Low" in df.columns:
            df = df[df["High"] >= df["Low"]]
        df = df[~df.index.duplicated(keep="last")]
        validation = validate_ohlcv(df)
        if not validation.valid:
            logger.warning(f"Validation issues for {symbol}: {validation.errors}")
        logger.info(f"{symbol}: {len(df)} bars | {df.index[0].date()} to {df.index[-1].date()}")
        return df

    def _find_col(self, df: pd.DataFrame, target: str) -> str | None:
        for alias in COLUMN_ALIASES.get(target, [target.title()]):
            if alias in df.columns:
                return alias
        for col in df.columns:
            if col.lower().startswith(target.lower()):
                return col
        return None

    def _filter(self, data: pd.DataFrame, start: str | None, end: str | None) -> pd.DataFrame:
        if start:
            data = data[data.index >= start]
        if end:
            data = data[data.index <= end]
        return data

    def _to_interval(self, data: pd.DataFrame, interval: str) -> pd.DataFrame:
        interval = interval.lower().strip()
        if interval in {"raw", "native"}:
            return data

        rule_map = {
            "1m": "1min",
            "2m": "2min",
            "5m": "5min",
            "15m": "15min",
            "30m": "30min",
            "60m": "60min",
            "1h": "1H",
            "1d": "1D",
            "d": "1D",
            "day": "1D",
            "daily": "1D",
            "1wk": "1W",
            "1w": "1W",
            "1mo": "1M",
        }
        rule = rule_map.get(interval)
        if rule is None:
            logger.warning(f"Unsupported CSV interval '{interval}', returning native bars")
            return data

        if data.empty or not isinstance(data.index, pd.DatetimeIndex):
            return data

        if interval in {"1d", "d", "day", "daily"}:
            has_intraday = (
                (data.index.hour != 0).any()
                or (data.index.minute != 0).any()
                or (data.index.second != 0).any()
            )
            if not has_intraday:
                return data

        agg = data.resample(rule).agg(
            {
                "Open": "first",
                "High": "max",
                "Low": "min",
                "Close": "last",
                "Volume": "sum",
            }
        )
        agg = agg.dropna(subset=["Open", "High", "Low", "Close"])
        agg = agg[agg["Volume"] >= 0]
        return agg

    def _parquet_path(self, symbol: str) -> Path:
        return self.processed_dir / f"{symbol.upper()}_daily.parquet"

    def _load_parquet(self, symbol: str) -> pd.DataFrame | None:
        p = self._parquet_path(symbol)
        if p.exists():
            try:
                return pd.read_parquet(p)
            except Exception:
                pass
        return None

    def _save_parquet(self, data: pd.DataFrame, symbol: str) -> None:
        try:
            data.to_parquet(self._parquet_path(symbol), compression="snappy")
        except Exception as e:
            logger.warning(f"Parquet save failed: {e}")
