"""Optional structured logger for strategy modules."""

from __future__ import annotations

from loguru import logger


def get_logger(name: str):
    """Bind module name for contextual logging."""
    return logger.bind(module=name)
