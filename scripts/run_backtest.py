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
logger.add(sys.stderr, level="INFO", colorize=True,
           format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | {message}")
logger.add("logs/backtest_{time:YYYYMMDD}.log", level="DEBUG", rotation="1 day")


def parse_args():
    p = argparse.ArgumentParser(description="Aram-TMS Backtest Runner")
    p.add_argument("--strategy", "-s", default="MomentumStrategy")
    p.add_argument("--engine", "-e", default="vectorbt",
                   choices=["vectorbt","backtrader","zipline"])
    p.add_argument("--start", default="2020-01-01")
    p.add_argument("--end", default=datetime.today().strftime("%Y-%m-%d"))
    p.add_argument("--capital", "-c", type=float, default=1_000_000)
    p.add_argument("--universe", "-u", default="nifty50",
                   choices=["nifty50","nifty100","midcap","custom"])
    p.add_argument("--symbols", nargs="+")
    p.add_argument("--data-source", default="auto",
                   choices=["yfinance","csv","auto"])
    p.add_argument("--mode", default="single",
                   choices=["single","walk_forward","optimize"])
    p.add_argument("--train-window", type=int, default=252)
    p.add_argument("--test-window", type=int, default=63)
    p.add_argument("--metric", default="sharpe",
                   choices=["sharpe","total_return","calmar","sortino"])
    p.add_argument("--output-dir", "-o", default="data/results/backtests")
    p.add_argument("--list-strategies", action="store_true")
    p.add_argument("--no-benchmark", action="store_true")
    return p.parse_args()


def get_symbols(args):
    from src.data.yfinance_loader import YFinanceLoader
    if args.universe == "custom" and args.symbols:
        return [f"{s}.NS" if "." not in s else s for s in args.symbols]
    yf = YFinanceLoader()
    return yf.get_nifty50_symbols()


def load_data(symbols, start, end, data_source, args):
    from src.data.yfinance_loader import YFinanceLoader
    from src.data.csv_loader import KaggleCSVLoader
    years = (datetime.strptime(end,"%Y-%m-%d")-datetime.strptime(start,"%Y-%m-%d")).days/365
    if data_source == "auto":
        data_source = "yfinance" if years <= 2 else "csv"
        logger.info(f"Auto data source: {data_source} ({years:.1f} years)")
    if data_source == "yfinance":
        loader = YFinanceLoader()
        return loader.fetch_universe(symbols, start=start, end=end)
    else:
        csv_loader = KaggleCSVLoader()
        available = csv_loader.list_available_symbols()
        if not available:
            logger.warning("No CSVs found — using yFinance")
            return YFinanceLoader().fetch_universe(symbols, start=start, end=end)
        result = {}
        yf = YFinanceLoader()
        for sym in symbols:
            clean = sym.replace(".NS","").replace(".BO","")
            try:
                if clean in available:
                    result[clean] = csv_loader.load(clean, start=start, end=end)
                else:
                    result[clean] = yf.fetch(sym, start=start, end=end)
            except Exception as e:
                logger.warning(f"Load failed {sym}: {e}")
        return result


def main():
    args = parse_args()

    # Register all strategies
    import src.strategies.library.momentum
    from src.strategies.base_strategy import STRATEGY_REGISTRY, list_strategies, get_strategy

    if args.list_strategies:
        print("\n📊 Available Strategies:")
        print("-"*55)
        for s in list_strategies():
            print(f"  {s['name']:<28} [{s['category']}] {s['timeframe']}")
        print()
        return

    if args.strategy not in STRATEGY_REGISTRY:
        logger.error(f"Strategy '{args.strategy}' not found. Use --list-strategies")
        sys.exit(1)

    strategy_class = STRATEGY_REGISTRY[args.strategy]
    strategy = strategy_class()

    logger.info("="*55)
    logger.info(f"  Strategy  : {strategy}")
    logger.info(f"  Engine    : {args.engine}")
    logger.info(f"  Period    : {args.start} -> {args.end}")
    logger.info(f"  Capital   : Rs.{args.capital:,.0f}")
    logger.info(f"  Universe  : {args.universe}")
    logger.info(f"  Mode      : {args.mode}")
    logger.info("="*55)

    symbols = get_symbols(args)
    logger.info(f"Universe: {len(symbols)} symbols")
    data_dict = load_data(symbols, args.start, args.end, args.data_source, args)
    if not data_dict:
        logger.error("No data loaded!"); sys.exit(1)
    logger.info(f"Data loaded: {len(data_dict)} symbols")

    benchmark_data = None
    if not args.no_benchmark:
        try:
            from src.data.yfinance_loader import YFinanceLoader
            benchmark_data = YFinanceLoader().fetch("^NSEI", start=args.start, end=args.end)
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
        data = list(data_dict.values())[0] if len(data_dict)==1 else data_dict
        result = runner.run(strategy, data, benchmark_data)
        result.save(args.output_dir)
        logger.success(f"Results saved to {args.output_dir}/")

    elif args.mode == "walk_forward":
        from src.backtesting.walk_forward import WalkForwardOptimizer
        param_space = getattr(strategy_class, "PARAM_SPACE", {
            "momentum_period": [126,189,252], "ema_period": [30,50,100]})
        data = list(data_dict.values())[0]
        opt = WalkForwardOptimizer(strategy_class, param_space,
            train_window=args.train_window, test_window=args.test_window, metric=args.metric)
        opt.run(data, benchmark_data)
        logger.success("Walk-forward complete!")

    elif args.mode == "optimize":
        from src.backtesting.vectorbt_runner import VectorBTRunner
        runner = VectorBTRunner(initial_capital=args.capital)
        param_grid = getattr(strategy_class, "PARAM_SPACE", {
            "momentum_period": [126,189,252], "ema_period": [30,50,100]})
        data = list(data_dict.values())[0]
        results = runner.optimize(strategy_class, data, param_grid, metric=args.metric)
        print("\n📊 Top Optimization Results:")
        print(results.to_string(index=False))
        logger.success("Optimization complete!")


if __name__ == "__main__":
    main()
