"""Live Trading Runner CLI - Aram-TMS.

This script requires explicit live confirmation and production credentials.
"""

from __future__ import annotations

import argparse
import signal
import sys
import time
from pathlib import Path

from loguru import logger

sys.path.insert(0, str(Path(__file__).parent.parent))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aram-TMS Live Trading Runner")
    parser.add_argument("--strategy", "-s", default="MomentumStrategy")
    parser.add_argument("--symbols", nargs="+", default=["RELIANCE", "TCS", "HDFCBANK", "INFY"])
    parser.add_argument("--capital", "-c", type=float, default=1_000_000)
    parser.add_argument("--scan-interval", type=int, default=30)
    parser.add_argument("--max-positions", type=int, default=5)
    parser.add_argument("--confirm-live", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.confirm_live:
        logger.error("Live mode requires --confirm-live")
        sys.exit(1)

    confirmation = input("Type CONFIRM_LIVE to continue: ").strip()
    if confirmation != "CONFIRM_LIVE":
        logger.error("Live confirmation failed")
        sys.exit(1)

    import src.strategies.library.momentum  # noqa: F401  # registers built-in strategies
    from src.forward_testing.runner import ForwardTestRunner
    from src.live_trading.dhan_live import DhanLiveClient
    from src.strategies.base_strategy import STRATEGY_REGISTRY

    if args.strategy not in STRATEGY_REGISTRY:
        logger.error(f"Strategy '{args.strategy}' not found")
        sys.exit(1)

    strategy = STRATEGY_REGISTRY[args.strategy]()
    runner = ForwardTestRunner(
        strategy=strategy,
        scan_interval_seconds=args.scan_interval,
        capital=args.capital,
        max_positions=args.max_positions,
    )
    runner.dhan = DhanLiveClient(confirm_live=True)

    logger.critical("LIVE TRADING SESSION STARTING")
    session = runner.start(symbols=args.symbols, run_until_market_close=True)

    def shutdown(sig: int, frame: object) -> None:
        logger.warning("Stopping live session...")
        runner.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)

    while session.is_active:
        status = runner.get_status() or {}
        logger.info(
            f"LIVE | P&L: Rs.{float(status.get('total_pnl', 0)):+,.0f} | "
            f"Trades: {int(status.get('total_trades', 0))} | "
            f"Positions: {int(status.get('open_positions', 0))}"
        )
        time.sleep(30)


if __name__ == "__main__":
    main()
