import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# Standardize path
sys.path.append(str(Path(__file__).parent))

from core.backtester import IntradayBacktester
from core.data_handler import DataHandler
from trading_system.experiments import BacktestResultStore
from trading_system.optimization import LLMAssistedRLOptimizer
from trading_system.shared.strategies import IntradayMomentumStrategy


def _metric_to_float(value: object) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.replace("₹", "").replace(",", "").replace("%", "").strip()
        try:
            return float(cleaned)
        except ValueError:
            return 0.0
    return 0.0


def _score_metrics(metrics: dict) -> float:
    total_return = _metric_to_float(metrics.get("Total Return %", 0.0))
    drawdown = abs(_metric_to_float(metrics.get("Max Drawdown %", 0.0)))
    profit_factor = _metric_to_float(metrics.get("Profit Factor", 0.0))
    win_rate = _metric_to_float(metrics.get("Win Rate %", 0.0))
    trades = _metric_to_float(metrics.get("Total Trades", 0.0))
    low_trade_penalty = max(0.0, 3.0 - trades) * 2.0

    return (
        total_return
        + (0.5 * profit_factor)
        + (0.1 * win_rate)
        - (0.8 * drawdown)
        - low_trade_penalty
    )


def _build_strategy(df, strategy_params: dict):
    return IntradayMomentumStrategy(df, params=strategy_params)


def run_backtest_pipeline(
    ticker: str,
    days: int,
    interval: str,
    initial_capital: float,
    risk_per_trade_pct: float,
    data_source: str = "csv",
    csv_path: str | None = None,
    sl_pct: float = 0.01,
    tp_pct: float = 0.03,
    tsl_pct: float = 0.005,
    slippage: float = 0.0005,
    commission: float = 20.0,
    quantity: int = 1,
    enable_run_storage: bool = False,
    optimize_with_rl: bool = False,
    optimization_budget: int = 10,
    use_llm_assist: bool = False,
    run_store_dir: str | None = None,
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
    if data_source == "csv":
        if csv_path is None:
            csv_path = str(Path(__file__).parent / "data" / "RELIANCE_minute.csv")
        df = handler.load_historical_csv(csv_path, start_str, end_str, interval=interval)
    else:
        df = handler.fetch_data(ticker, start_date=start_str, end_date=end_str, interval=interval)

    if df.empty:
        print("Empty DataFrame returned. Exiting.")
        return

    print(f"Data Points Loaded: {len(df)}")

    # 2. Strategy Engine
    print("\n[2] Generating Technical Indicators & Signals (Intraday Momentum)...")
    # Modification Interface: Easily swap strategies or params here
    strategy_params = {
        "supertrend_period": 10,
        "supertrend_multiplier": 3.0,
        "rsi_period": 14,
        "ema_period": 9,
    }
    strategy = _build_strategy(df, strategy_params)
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
    def run_once(exec_params: dict):
        backtester = IntradayBacktester(
            data_with_signals,
            initial_capital=initial_capital,
            risk_per_trade_pct=float(exec_params["risk_per_trade_pct"]),
            sl_pct=float(exec_params["sl_pct"]),
            tp_pct=float(exec_params["tp_pct"]),
            tsl_pct=float(exec_params["tsl_pct"]),
            slippage=float(exec_params["slippage"]),
            commission=float(exec_params["commission"]),
            quantity=int(exec_params["quantity"]),
        )
        return backtester.run()

    run_store = None
    run_id = None
    if enable_run_storage or optimize_with_rl:
        store_root = run_store_dir or str(Path(__file__).parent / "runs")
        run_store = BacktestResultStore(store_root)
        run_id = run_store.start_run(
            {
                "ticker": ticker,
                "interval": interval,
                "start": start_str,
                "end": end_str,
                "initial_capital": initial_capital,
                "strategy": "IntradayMomentumStrategy",
                "strategy_params": strategy_params,
                "optimize_with_rl": optimize_with_rl,
                "optimization_budget": optimization_budget,
            }
        )

    execution_params = {
        "risk_per_trade_pct": risk_per_trade_pct,
        "sl_pct": sl_pct,
        "tp_pct": tp_pct,
        "tsl_pct": tsl_pct,
        "slippage": slippage,
        "commission": commission,
        "quantity": quantity,
    }

    if optimize_with_rl:
        parameter_space: dict[str, list[Any]] = {
            "risk_per_trade_pct": sorted(
                {
                    max(0.001, risk_per_trade_pct * 0.6),
                    risk_per_trade_pct,
                    min(0.05, risk_per_trade_pct * 1.4),
                }
            ),
            "sl_pct": sorted({max(0.002, sl_pct * 0.7), sl_pct, min(0.05, sl_pct * 1.3)}),
            "tp_pct": sorted({max(0.004, tp_pct * 0.7), tp_pct, min(0.1, tp_pct * 1.3)}),
            "tsl_pct": sorted({max(0.001, tsl_pct * 0.7), tsl_pct, min(0.03, tsl_pct * 1.3)}),
            "slippage": sorted({max(0.0, slippage * 0.7), slippage, min(0.01, slippage * 1.4)}),
            "commission": sorted({max(0.0, commission * 0.7), commission, commission * 1.3}),
            "quantity": [max(1, quantity)],
        }

        optimizer = LLMAssistedRLOptimizer(
            parameter_space=parameter_space,
            llm_endpoint=os.getenv("LLM_OPT_ENDPOINT") if use_llm_assist else None,
            llm_api_key=os.getenv("LLM_API_KEY") if use_llm_assist else None,
            llm_model=os.getenv("LLM_MODEL", "gpt-4o-mini") if use_llm_assist else None,
        )

        def evaluate(params: dict):
            trial_tearsheet, trial_metrics = run_once(params)
            score = _score_metrics(trial_metrics)
            details = {"metrics": trial_metrics}
            if run_store is not None and run_id is not None:
                run_store.append_trial(
                    run_id,
                    {
                        "params": params,
                        "score": score,
                        "metrics": trial_metrics,
                        "trades": len(trial_tearsheet) if trial_tearsheet is not None else 0,
                    },
                )
            return score, details

        result = optimizer.optimize(evaluate_fn=evaluate, budget=optimization_budget)
        execution_params.update(result.best_params)
        print(f"RL optimization best score: {result.best_score:.4f}")

    # Run the final backtest and get results (Tuple of Trades DataFrame, Metrics Dict)
    tearsheet, stats = run_once(execution_params)

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

    if run_store is not None and run_id is not None:
        run_store.save_backtest(
            run_id,
            metrics=stats,
            tearsheet=tearsheet,
            params={
                "strategy": strategy_params,
                "execution": execution_params,
            },
            extra={
                "signals": signals_count,
                "ticker": ticker,
                "data_source": data_source,
            },
        )
        run_store.finalize_run(
            run_id,
            status="completed",
            best_score=_score_metrics(stats),
            best_params=execution_params,
        )
        print(f"Run artifacts stored under: {Path(run_store.root_dir) / run_id}")


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
    DATA_SOURCE = "csv"  # "csv" or "yfinance"
    CSV_PATH = str(Path(__file__).parent / "data" / "RELIANCE_minute.csv")
    SL_PCT = 0.01
    TP_PCT = 0.03
    TSL_PCT = 0.005
    SLIPPAGE = 0.0005
    COMMISSION = 20.0
    QUANTITY = 1

    run_backtest_pipeline(
        ticker=TICKER,
        days=DAYS_BACK,
        interval=INTERVAL,
        initial_capital=INITIAL_CAPITAL,
        risk_per_trade_pct=RISK_PER_TRADE_PCT,
        data_source=DATA_SOURCE,
        csv_path=CSV_PATH,
        sl_pct=SL_PCT,
        tp_pct=TP_PCT,
        tsl_pct=TSL_PCT,
        slippage=SLIPPAGE,
        commission=COMMISSION,
        quantity=QUANTITY,
        enable_run_storage=True,
        optimize_with_rl=True,
        optimization_budget=12,
        use_llm_assist=False,
    )
