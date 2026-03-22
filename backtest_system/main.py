import sys
from datetime import datetime, timedelta
from pathlib import Path

# Standardize path
sys.path.append(str(Path(__file__).parent))

from core.backtester import IntradayBacktester
from core.data_handler import DataHandler
from strategies.intraday_momentum_strategy import IntradayMomentumStrategy


def run_backtest_pipeline(
    ticker: str, days: int, interval: str, initial_capital: float, risk_per_trade_pct: float
):
    print("=" * 60)
    print("🚀 MODULAR RETAIL ALGORITHMIC BACKTESTING SYSTEM")
    print("=" * 60)

    # 1. Fetch Data
    handler = DataHandler(data_dir=Path(__file__).parent / "data")
    end = datetime.now()
    start = end - timedelta(days=days)

    start_str = start.strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")

    print(f"\n[1] Fetching {ticker} ({interval}) Data from {start_str} to {end_str}...")
    df = handler.fetch_data(ticker, start_date=start_str, end_date=end_str, interval=interval)

    if df.empty:
        print("Empty DataFrame returned. Exiting.")
        return

    print(f"Data Points Loaded: {len(df)}")

    # 2. Strategy Engine
    print("\n[2] Generating Technical Indicators & Signals (Intraday Momentum)...")
    # Modification Interface: Easily swap strategies or params here
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

    signals_count = len(data_with_signals[data_with_signals["signal"] != 0])
    print(f"Total Signals Generated: {signals_count}")

    if signals_count == 0:
        print("No signals generated. Exiting.")
        return

    # 3. Backtesting Engine
    print(
        "\n[3] Running Intraday Event-Driven Execution Engine (incorporating Slippage, Brokerage, STT, Taxes)..."
    )
    # Modification Interface: Easily tweak Risk Management params here
    backtester = IntradayBacktester(
        data_with_signals,
        initial_capital=initial_capital,
        risk_per_trade_pct=risk_per_trade_pct,
        sl_pct=0.01,  # 1% Strict SL
        tp_pct=0.03,  # 3% Take Profit
        tsl_pct=0.005,  # 0.5% Trailing SL
        slippage=0.0005,  # 0.05% Slippage
    )

    # Run the backtest and get results (Tuple of Trades DataFrame, Metrics Dict)
    tearsheet, stats = backtester.run()

    print(f"Execution Complete. Total Trades Executed: {stats.get('Total Trades', 0)}")

    # 4. Analytics & Tearsheet
    print("\n[4] Generating Performance Analytics...")

    if tearsheet is not None and not tearsheet.empty:
        # Save simple CSV of trades
        data_dir = Path(__file__).parent / "data"
        data_dir.mkdir(exist_ok=True)
        trades_curr_file = data_dir / f"{ticker}_trades.csv"
        tearsheet.to_csv(trades_curr_file, index=False)
        print(f"Detailed Trade log saved to {trades_curr_file}")

        print("\n" + "=" * 40)
        print("PERFORMANCE METRICS")
        print("=" * 40)
        for k, v in stats.items():
            print(f"{k}: {v}")
    else:
        print("No trades were executed.")


if __name__ == "__main__":
    # ---------------------------------------------------------
    # MODIFICATION INTERFACE
    # Change these variables to quickly test new scenarios
    # ---------------------------------------------------------
    TICKER = "RELIANCE"
    # yfinance 1m data is limited to 7 days, using larger lookback for daily if needed
    DAYS_BACK = 5
    INTERVAL = "1m"
    INITIAL_CAPITAL = 100000.0
    RISK_PER_TRADE_PCT = 0.01  # 1% Risk per trade

    run_backtest_pipeline(
        ticker=TICKER,
        days=DAYS_BACK,
        interval=INTERVAL,
        initial_capital=INITIAL_CAPITAL,
        risk_per_trade_pct=RISK_PER_TRADE_PCT,
    )
