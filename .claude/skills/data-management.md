# Skill: Data Management — Aram-TMS

## Data Priority Order
1. data/processed/*.parquet (fastest — check first)
2. data/raw/csv/*.csv (Kaggle long-term data)
3. yFinance download (fresh, <2yr)
4. DhanHQ API (live/forward only)

## yFinance Loader
```python
from src.data.yfinance_loader import YFinanceLoader
loader = YFinanceLoader(cache_dir="data/cache/")
data = loader.fetch("RELIANCE.NS", start="2022-01-01", end="2024-12-31", interval="1d")
universe = loader.fetch_universe(["RELIANCE.NS","TCS.NS"], start="2023-01-01", end="2024-12-31")
nifty = loader.fetch_index("NIFTY50", start="2020-01-01")
```

## Kaggle CSV Loader
```python
from src.data.csv_loader import KaggleCSVLoader
loader = KaggleCSVLoader(data_dir="data/raw/csv/")
data = loader.load("RELIANCE", start="2010-01-01", end="2024-12-31")
all_data = loader.load_all_available()
available = loader.list_available_symbols()
desc = loader.describe_dataset()
```

## Expected CSV Format
Date,Open,High,Low,Close,Volume
2010-01-04,1065.50,1087.50,1060.00,1080.25,4523100
Accepted variants: date/DATE, open/OPEN, Close/CLOSE/Last/LTP, Vol/VOLUME
File naming: RELIANCE.csv | RELIANCE_NSE.csv | RELIANCE_daily.csv

## Caching Pattern
Always cache to parquet after download:
data.to_parquet("data/processed/RELIANCE_daily.parquet", compression="snappy")
cached = pd.read_parquet("data/processed/RELIANCE_daily.parquet")

## Backtesting Data Rules
1. Add extra warmup bars before strategy start (e.g. 200-day MA needs 200 extra)
2. Leave 6-12 months out-of-sample — never use for optimization
3. Use as-of dates for fundamental data (point-in-time)
4. Only ffill max 3 days for equity data
