"""
Forward Test Runner CLI - Aram-TMS
Launches paper trading via DhanHQ Sandbox.

Usage:
  python scripts/run_forward_test.py --strategy MomentumStrategy
  python scripts/run_forward_test.py --symbols RELIANCE TCS HDFCBANK INFY
  python scripts/run_forward_test.py --run-hours 6.5
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import signal
import time
from datetime import datetime
from loguru import logger

logger.remove()
logger.add(sys.stderr, level="INFO", colorize=True,
           format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | {message}")
logger.add("logs/forward_test_{time:YYYYMMDD}.log", level="DEBUG", rotation="1 day")


def parse_args():
    p = argparse.ArgumentParser(description="Aram-TMS Forward Test Runner")
    p.add_argument("--strategy", "-s", default="MomentumStrategy")
    p.add_argument("--symbols", nargs="+", default=["RELIANCE","TCS","HDFCBANK","INFY"])
    p.add_argument("--capital", "-c", type=float, default=500_000)
    p.add_argument("--run-hours", type=float, default=None)
    p.add_argument("--scan-interval", type=int, default=60)
    p.add_argument("--max-positions", type=int, default=5)
    p.add_argument("--data-interval", default="5m")
    return p.parse_args()


def main():
    args = parse_args()

    import src.strategies.library.momentum
    from src.strategies.base_strategy import STRATEGY_REGISTRY

    if args.strategy not in STRATEGY_REGISTRY:
        logger.error(f"Strategy '{args.strategy}' not found")
        sys.exit(1)

    strategy = STRATEGY_REGISTRY[args.strategy]()

    logger.info("="*55)
    logger.info("  ARAM-TMS FORWARD TEST — DhanHQ Sandbox")
    logger.info(f"  Strategy  : {strategy}")
    logger.info(f"  Symbols   : {args.symbols}")
    logger.info(f"  Capital   : Rs.{args.capital:,.0f}")
    logger.info(f"  Scan      : every {args.scan_interval}s")
    logger.info("="*55)

    now = datetime.now()
    is_market = (now.weekday()<5 and
                 now.replace(hour=9,minute=15)<=now<=now.replace(hour=15,minute=30))
    if not is_market:
        logger.warning(f"Market CLOSED — {now.strftime('%H:%M IST')} (Mon-Fri 9:15-15:30)")
        ans = input("Continue anyway for testing? [y/N]: ")
        if ans.lower() != "y":
            sys.exit(0)

    try:
        from src.forward_testing.runner import ForwardTestRunner
        runner = ForwardTestRunner(
            strategy=strategy,
            scan_interval_seconds=args.scan_interval,
            data_interval=args.data_interval,
            capital=args.capital,
            max_positions=args.max_positions)
    except Exception as e:
        logger.error(f"Init failed: {e}")
        logger.error("Check DHAN_SANDBOX_CLIENT_ID and DHAN_SANDBOX_ACCESS_TOKEN in .env")
        sys.exit(1)

    def shutdown(sig, frame):
        logger.info("Ctrl+C — stopping session...")
        runner.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)

    session = runner.start(symbols=args.symbols, run_hours=args.run_hours,
                            run_until_market_close=True)
    logger.info(f"Session ID: {session.session_id}")

    while session.is_active:
        status = runner.get_status()
        if status:
            logger.info(f"P&L: Rs.{status.get('total_pnl',0):+,.0f} | "
                        f"Trades: {status.get('total_trades',0)} | "
                        f"Positions: {status.get('open_positions',0)}")
        time.sleep(60)

    logger.success("Forward test session ended")


if __name__ == "__main__":
    main()
