"""
Backtest Runner CLI - Aram-TMS
Usage:
  python scripts/run_backtest.py --strategy MomentumStrategy
  python scripts/run_backtest.py --strategy MomentumStrategy --start 2018-01-01 --end 2024-12-31
  python scripts/run_backtest.py --mode walk_forward
  python scripts/run_backtest.py --list-strategies
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
from datetime import datetime

from loguru import logger

logger.remove()
logger.add(
    sys.stderr,
    level="INFO",
    colorize=True,
    format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | {message}",
)
logger.add("logs/backtest_{time:YYYYMMDD}.log", level="DEBUG", rotation="1 day")


def parse_args():
    p = argparse.ArgumentParser(description="Aram-TMS Backtest Runner")
    p.add_argument("--strategy", "-s", default="MomentumStrategy")
    p.add_argument(
        "--engine", "-e", default="vectorbt", choices=["vectorbt", "backtrader", "zipline"]
    )
    p.add_argument("--start", default="2020-01-01")
    p.add_argument("--end", default=datetime.today().strftime("%Y-%m-%d"))
    p.add_argument(
        "--timeframe",
        default="1d",
        choices=["1m", "5m", "15m", "30m", "1h", "1d", "1wk", "1mo"],
    )
    p.add_argument("--capital", "-c", type=float, default=1_000_000)
    p.add_argument(
        "--universe", "-u", default="custom", choices=["nifty50", "nifty100", "midcap", "custom"]
    )
    p.add_argument("--symbols", nargs="+")
    p.add_argument("--data-source", default="auto", choices=["yfinance", "csv", "auto"])
    p.add_argument("--mode", default="single", choices=["single", "walk_forward", "optimize"])
    p.add_argument("--train-window", type=int, default=252)
    p.add_argument("--test-window", type=int, default=63)
    p.add_argument(
        "--metric", default="sharpe", choices=["sharpe", "total_return", "calmar", "sortino"]
    )
    p.add_argument("--output-dir", "-o", default="data/results/backtests")
    p.add_argument("--list-strategies", action="store_true")
    p.add_argument("--no-benchmark", action="store_true")
    return p.parse_args()


def get_symbols(args):
    if args.symbols:
        picked = [f"{s}.NS" if "." not in s else s for s in args.symbols]
    else:
        picked = ["RELIANCE.NS"]
        logger.warning("No symbol passed; defaulting to RELIANCE.NS")
    if len(picked) > 1:
        logger.warning(f"Single-symbol backtesting enforced. Using first symbol only: {picked[0]}")
    return picked[:1]


def load_data(symbols, start, end, data_source, args):
    from src.data.csv_loader import KaggleCSVLoader
    from src.data.yfinance_loader import YFinanceLoader

    years = (datetime.strptime(end, "%Y-%m-%d") - datetime.strptime(start, "%Y-%m-%d")).days / 365
    if data_source == "auto":
        data_source = "yfinance" if years <= 2 else "csv"
        logger.info(f"Auto data source: {data_source} ({years:.1f} years)")
    if data_source == "yfinance":
        loader = YFinanceLoader(auto_adjust=False)
        sym = symbols[0]
        clean = sym.replace(".NS", "").replace(".BO", "")
        df = loader.fetch(sym, start=start, end=end, interval=args.timeframe, use_cache=False)
        return {clean: df} if not df.empty else {}
    else:
        csv_loader = KaggleCSVLoader()
        if not csv_loader.list_available_symbols():
            logger.warning("No CSVs found — using yFinance")
            yf = YFinanceLoader(auto_adjust=False)
            sym = symbols[0]
            clean = sym.replace(".NS", "").replace(".BO", "")
            df = yf.fetch(sym, start=start, end=end, interval=args.timeframe, use_cache=False)
            return {clean: df} if not df.empty else {}

        sym = symbols[0]
        clean = sym.replace(".NS", "").replace(".BO", "")
        try:
            df = csv_loader.load(
                clean,
                start=start,
                end=end,
                interval=args.timeframe,
                use_cache=False,
            )
            logger.info(f"Using CSV source for {clean}")
        except TypeError as e:
            if "unexpected keyword argument 'interval'" not in str(e):
                raise
            logger.warning("CSV loader does not accept 'interval'; using compatibility fallback")
            df = csv_loader.load(clean, start=start, end=end, use_cache=False)
            if hasattr(csv_loader, "_to_interval"):
                df = csv_loader._to_interval(df, args.timeframe)
        except Exception as e:
            logger.warning(f"CSV load failed for {clean} ({e}); falling back to yFinance")
            df = YFinanceLoader(auto_adjust=False).fetch(
                sym, start=start, end=end, interval=args.timeframe, use_cache=False
            )
        return {clean: df} if not df.empty else {}


def main():
    args = parse_args()

    # Register all strategies
    from src.strategies.base_strategy import STRATEGY_REGISTRY, list_strategies

    if args.list_strategies:
        print("\n📊 Available Strategies:")
        print("-" * 55)
        for s in list_strategies():
            print(f"  {s['name']:<28} [{s['category']}] {s['timeframe']}")
        print()
        return

    if args.strategy not in STRATEGY_REGISTRY:
        logger.error(f"Strategy '{args.strategy}' not found. Use --list-strategies")
        sys.exit(1)

    strategy_class = STRATEGY_REGISTRY[args.strategy]
    strategy = strategy_class()

    logger.info("=" * 55)
    logger.info(f"  Strategy  : {strategy}")
    logger.info(f"  Engine    : {args.engine}")
    logger.info(f"  Period    : {args.start} -> {args.end}")
    logger.info(f"  Timeframe : {args.timeframe}")
    logger.info(f"  Capital   : Rs.{args.capital:,.0f}")
    logger.info(f"  Universe  : {args.universe} (ignored in single-symbol mode)")
    logger.info(f"  Mode      : {args.mode}")
    logger.info("=" * 55)

    symbols = get_symbols(args)
    logger.info(f"Symbol: {symbols[0]}")
    data_dict = load_data(symbols, args.start, args.end, args.data_source, args)
    if not data_dict:
        logger.error("No data loaded! Running diagnostics...")
        sym = symbols[0].replace(".NS", "").replace(".BO", "")
        try:
            from src.data.csv_loader import KaggleCSVLoader

            meta = KaggleCSVLoader().inspect_symbol(sym)
            logger.error(
                f"CSV diagnostic | exists={meta.get('exists')} | path={meta.get('path')} | "
                f"range={meta.get('start')}..{meta.get('end')} | rows={meta.get('rows')}"
            )
        except Exception as e:
            logger.warning(f"CSV diagnostics failed: {e}")
        logger.error(
            "For yFinance: verify symbol/network/timeframe window. "
            "For CSV: verify file, OHLCV columns, and date overlap."
        )
        sys.exit(1)
    logger.info(f"Data loaded: {len(data_dict)} symbols")

    warmup = strategy.get_warmup_period()
    lengths = {sym: len(df) for sym, df in data_dict.items()}
    short_symbols = [sym for sym, bars in lengths.items() if bars < warmup]
    if short_symbols:
        logger.warning(
            f"Insufficient bars for warmup={warmup}. "
            f"Potentially no/limited signals for: {short_symbols[:10]}"
        )

    benchmark_data = None
    if not args.no_benchmark:
        try:
            from src.data.yfinance_loader import YFinanceLoader

            benchmark_data = YFinanceLoader(auto_adjust=False).fetch(
                "^NSEI", start=args.start, end=args.end, interval="1d", use_cache=False
            )
            logger.info(f"Benchmark: NIFTY 50 ({len(benchmark_data)} bars)")
        except Exception as e:
            logger.warning(f"Benchmark failed: {e}")

    if args.mode == "single":
        if args.engine == "vectorbt":
            from src.backtesting.vectorbt_runner import VectorBTRunner

            runner = VectorBTRunner(initial_capital=args.capital)
        else:
            from src.backtesting.backtrader_runner import BacktraderRunner

            runner = BacktraderRunner(initial_capital=args.capital)
        data = list(data_dict.values())[0] if len(data_dict) == 1 else data_dict
        result = runner.run(strategy, data, benchmark_data)
        result.timeframe = args.timeframe
        result.data_source = args.data_source
        result.symbols = list(data_dict.keys())
        if isinstance(data, dict):
            result.bars_loaded = int(sum(len(df) for df in data.values()))
        else:
            result.bars_loaded = int(len(data))
        result.warmup_required = int(warmup)
        result.save(args.output_dir)
        logger.success(f"Results saved to {args.output_dir}/")

    elif args.mode == "walk_forward":
        from src.backtesting.walk_forward import WalkForwardOptimizer

        param_space = getattr(
            strategy_class,
            "PARAM_SPACE",
            {"momentum_period": [126, 189, 252], "ema_period": [30, 50, 100]},
        )
        data = list(data_dict.values())[0]
        opt = WalkForwardOptimizer(
            strategy_class,
            param_space,
            train_window=args.train_window,
            test_window=args.test_window,
            metric=args.metric,
        )
        opt.run(data, benchmark_data)
        logger.success("Walk-forward complete!")

    elif args.mode == "optimize":
        from src.backtesting.vectorbt_runner import VectorBTRunner

        runner = VectorBTRunner(initial_capital=args.capital)
        param_grid = getattr(
            strategy_class,
            "PARAM_SPACE",
            {"momentum_period": [126, 189, 252], "ema_period": [30, 50, 100]},
        )
        data = list(data_dict.values())[0]
        results = runner.optimize(strategy_class, data, param_grid, metric=args.metric)
        print("\n📊 Top Optimization Results:")
        print(results.to_string(index=False))
        logger.success("Optimization complete!")


if __name__ == "__main__":
    main()
