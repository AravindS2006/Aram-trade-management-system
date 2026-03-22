"""
Kaggle CSV Data Loader - Aram-TMS
Loads long-term historical NSE/BSE data from downloaded Kaggle CSV files.
"""
from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Optional, Union
import pandas as pd
import numpy as np
from loguru import logger

COLUMN_ALIASES = {
    "open": ["Open","OPEN","open","Open Price"],
    "high": ["High","HIGH","high","High Price"],
    "low": ["Low","LOW","low","Low Price"],
    "close": ["Close","CLOSE","close","Close Price","Last","LTP"],
    "volume": ["Volume","VOLUME","volume","Vol","No of Shares"],
    "date": ["Date","DATE","date","Datetime","timestamp","Time","TIMESTAMP"],
}


class KaggleCSVLoader:
    """
    Loads long-term historical market data from Kaggle CSV files.

    Expected file location: data/raw/csv/
    Naming: RELIANCE.csv | RELIANCE_NSE.csv | RELIANCE_daily.csv
    Required columns: Date, Open, High, Low, Close, Volume (names flexible)
    """
    def __init__(self, data_dir: Union[str, Path] = "data/raw/csv",
                 processed_dir: Union[str, Path] = "data/processed") -> None:
        self.data_dir = Path(data_dir)
        self.processed_dir = Path(processed_dir)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        if self.data_dir.exists():
            n = len(list(self.data_dir.glob("*.csv")))
            logger.info(f"KaggleCSVLoader: {n} CSV files in {self.data_dir}")
        else:
            logger.warning(f"CSV dir not found: {self.data_dir}")

    def load(self, symbol: str, start: Optional[str] = None,
             end: Optional[str] = None, use_cache: bool = True) -> pd.DataFrame:
        """Load data for a symbol from CSV. Caches to parquet for speed."""
        if use_cache:
            cached = self._load_parquet(symbol)
            if cached is not None:
                return self._filter(cached, start, end)
        csv_path = self._find_csv(symbol)
        if csv_path is None:
            raise FileNotFoundError(
                f"No CSV for '{symbol}' in {self.data_dir}. "
                f"Available: {self.list_available_symbols()[:10]}")
        data = self._read_csv(csv_path, symbol)
        if use_cache and not data.empty:
            self._save_parquet(data, symbol)
        return self._filter(data, start, end)

    def load_all_available(self, start: Optional[str] = None,
                           end: Optional[str] = None) -> Dict[str, pd.DataFrame]:
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

    def list_available_symbols(self) -> List[str]:
        if not self.data_dir.exists(): return []
        syms = []
        for f in sorted(self.data_dir.glob("*.csv")):
            name = f.stem.upper()
            for suf in ["_NSE","_BSE","_DAILY","_1D","_EOD"]:
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
                    rows.append({"Symbol": sym, "File": p.name,
                                 "Size_MB": round(p.stat().st_size/1e6, 2),
                                 "Start": df.index[0].date() if not df.empty else None,
                                 "End": df.index[-1].date() if not df.empty else None,
                                 "Bars": len(df)})
            except Exception: pass
        return pd.DataFrame(rows)

    def _find_csv(self, symbol: str) -> Optional[Path]:
        sym = symbol.upper().replace(".NS","").replace(".BO","")
        for pat in [f"{sym}.csv", f"{sym}_NSE.csv", f"{sym}_daily.csv",
                    f"{sym}_EOD.csv", f"{sym.lower()}.csv"]:
            p = self.data_dir / pat
            if p.exists(): return p
        for f in self.data_dir.glob("*.csv"):
            if f.stem.upper().startswith(sym): return f
        return None

    def _read_csv(self, path: Path, symbol: str) -> pd.DataFrame:
        df = pd.read_csv(path, low_memory=False)
        date_col = self._find_col(df, "date")
        if date_col is None:
            raise ValueError(f"No date column in {path}. Cols: {list(df.columns)}")
        df = df.rename(columns={date_col: "Date"})
        df["Date"] = pd.to_datetime(df["Date"], infer_datetime_format=True, dayfirst=True)
        df = df.set_index("Date").sort_index()
        if hasattr(df.index,"tz") and df.index.tz:
            df.index = df.index.tz_localize(None)
        renames = {}
        for target in ["open","high","low","close","volume"]:
            col = self._find_col(df, target)
            if col: renames[col] = target.title()
            elif target == "volume": df["Volume"] = 0
        df = df.rename(columns=renames)
        avail = [c for c in ["Open","High","Low","Close","Volume"] if c in df.columns]
        df = df[avail].copy()
        for col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(",",""), errors="coerce")
        df = df[df.index.dayofweek < 5]
        df = df[df["Close"] > 0].dropna(subset=["Close"])
        if "High" in df.columns and "Low" in df.columns:
            df = df[df["High"] >= df["Low"]]
        df = df[~df.index.duplicated(keep="last")]
        logger.info(f"{symbol}: {len(df)} bars | {df.index[0].date()} to {df.index[-1].date()}")
        return df

    def _find_col(self, df: pd.DataFrame, target: str) -> Optional[str]:
        for alias in COLUMN_ALIASES.get(target, [target.title()]):
            if alias in df.columns: return alias
        for col in df.columns:
            if col.lower().startswith(target.lower()): return col
        return None

    def _filter(self, data: pd.DataFrame, start: Optional[str], end: Optional[str]) -> pd.DataFrame:
        if start: data = data[data.index >= start]
        if end: data = data[data.index <= end]
        return data

    def _parquet_path(self, symbol: str) -> Path:
        return self.processed_dir / f"{symbol.upper()}_daily.parquet"

    def _load_parquet(self, symbol: str) -> Optional[pd.DataFrame]:
        p = self._parquet_path(symbol)
        if p.exists():
            try: return pd.read_parquet(p)
            except Exception: pass
        return None

    def _save_parquet(self, data: pd.DataFrame, symbol: str) -> None:
        try: data.to_parquet(self._parquet_path(symbol), compression="snappy")
        except Exception as e: logger.warning(f"Parquet save failed: {e}")
