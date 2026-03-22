"""Aram Trade Management System"""
__version__ = "1.0.0"

from src.strategies.base_strategy import (
    BaseStrategy, Signal, SignalType,
    register_strategy, get_strategy, list_strategies, STRATEGY_REGISTRY)

try:
    import src.strategies.library.momentum
except ImportError:
    pass

__all__ = ["BaseStrategy","Signal","SignalType","register_strategy",
           "get_strategy","list_strategies","STRATEGY_REGISTRY"]
