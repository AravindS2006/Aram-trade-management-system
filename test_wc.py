import pandas as pd
from strategies.weapon_candle_system_strategy import WeaponCandleSystemStrategy
from core.backtester import IntradayBacktester

try:
    print("Loading data...")
    df = pd.read_csv("data/RELIANCE_minute.csv", parse_dates=["date"], index_col="date")
    df = df.sort_index()
    # rename if needed
    rename_cols = {c: c.lower() for c in df.columns}
    df = df.rename(columns=rename_cols)
    print("Resampling...")
    df_5m = df.resample('5min', closed='left', label='left').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna()
    print("Data length:", len(df_5m))

    strategy = WeaponCandleSystemStrategy(df_5m)
    data_with_signals = strategy.get_data_with_signals()
    
    num_signals = (data_with_signals['signal'] != 0).sum()
    print(f"Generated {num_signals} signals")

    if num_signals > 0:
        bt = IntradayBacktester(data_with_signals, initial_capital=500000)
        df_trades, metrics = bt.run()
        if metrics:
            print(metrics)
        else:
            print("No trades generated in metrics.")
except Exception as e:
    import traceback
    traceback.print_exc()
