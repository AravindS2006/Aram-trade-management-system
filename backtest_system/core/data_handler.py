from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pytz
import yfinance as yf


class DataHandler:
    """
    Handles intraday data fetching, caching, and preprocessing for Indian Equity Markets.
    """
    def __init__(self, data_dir: str | Path | None = None):
        # Default to the project-local data directory regardless of current working directory.
        if data_dir is None:
            data_dir = Path(__file__).parent.parent / "data"
        self.data_dir = Path(data_dir).resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.tz_ist = pytz.timezone('Asia/Kolkata')
        
    def fetch_data(self, ticker: str, start_date: str, end_date: str, interval: str = "1m", use_cache: bool = True) -> pd.DataFrame:
        """
        Fetches historical data for a given ticker, caches it, and strictly filters for NSE market hours.
        Note: yfinance '1m' data is only available for the last 7 days.
        
        start_date, end_date format: 'YYYY-MM-DD'
        interval: '1m', '5m', '15m'
        """
        # Ensure ticker format for Yahoo Finance (NSE stocks end with .NS)
        yf_ticker = ticker if ticker.endswith('.NS') else f"{ticker}.NS"
        
        file_name = f"{ticker}_{interval}_{start_date}_{end_date}.parquet"
        file_path = self.data_dir / file_name
        
        if use_cache and file_path.exists():
            print(f"Loading cached {interval} data for {ticker} from {file_path}")
            return pd.read_parquet(file_path)
            
        print(f"Downloading {interval} data for {ticker} from yfinance...")
        df = yf.download(yf_ticker, start=start_date, end=end_date, interval=interval, progress=False)
        
        if df.empty:
            print(f"Warning: No data found for {ticker} between {start_date} and {end_date}.")
            return df
            
        # yfinance might return MultiIndex columns for a single ticker in recent versions
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
            
        # Standardize timezone to IST
        if df.index.tz is None:
            df.index = df.index.tz_localize('UTC').tz_convert(self.tz_ist)
        else:
            df.index = df.index.tz_convert(self.tz_ist)
            
        # Filter for NSE Market Hours (9:15 to 15:30)
        # Note: yfinance often returns full 24h data for some assets or pre-market.
        market_open = datetime.strptime("09:15", "%H:%M").time()
        market_close = datetime.strptime("15:30", "%H:%M").time()
        
        df = df[
            (df.index.time >= market_open) & 
            (df.index.time <= market_close)
        ]
        
        # Cache the cleaned data
        print(f"Caching data to {file_path}")
        df.to_parquet(file_path)
        
        return df

    def load_csv(self, file_path: str) -> pd.DataFrame:
        """
        Load data from a local CSV file.
        Expected format: Date/Time index, Open, High, Low, Close, Volume
        """
        path = Path(file_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
            
        df = pd.read_csv(path, parse_dates=True, index_col=0)
        # Ensure column names are standard Capitalized
        df.columns = [c.capitalize() for c in df.columns]
        return df

if __name__ == "__main__":
    # Quick Test Execution
    handler = DataHandler(data_dir=Path(__file__).parent.parent / "data")
    
    # yfinance only provides 1m data for the last 7 days.
    end = datetime.now()
    start = end - timedelta(days=5)
    
    start_str = start.strftime('%Y-%m-%d')
    end_str = end.strftime('%Y-%m-%d')
    
    try:
        df = handler.fetch_data("RELIANCE", start_date=start_str, end_date=end_str, interval="1m")
        print("\nData Sample (First 5 rows):")
        pd.set_option("display.max_columns", None)
        print(df.head())
        print(f"\nTotal Rows Validated during Market Hours: {len(df)}")
        print(f"Time Range: {df.index.min()} to {df.index.max()}")
    except Exception as e:
        print(f"Test failed: {e}")
