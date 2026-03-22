from __future__ import annotations

from loguru import logger


def configure_logger() -> None:
    logger.remove()
    logger.add(
        "logs/ichimoku_strategy.log",
        rotation="10 MB",
        retention=10,
        enqueue=True,
        level="INFO",
    )


def log_trade(signal: dict, order: dict) -> None:
    logger.info("Trade signal={} order={}", signal, order)

