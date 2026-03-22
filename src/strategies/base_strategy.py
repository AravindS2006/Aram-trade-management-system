"""
Base Strategy - Aram Trade Management System
All trading strategies must inherit from BaseStrategy.
"""
from __future__ import annotations
import abc
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from loguru import logger


class SignalType(Enum):
    LONG = 1
    FLAT = 0
    SHORT = -1


class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "SL"
    STOP_LIMIT = "SL-M"


class ProductType(Enum):
    DELIVERY = "CNC"
    INTRADAY = "INTRA"
    MARGIN = "MARGIN"


@dataclass
class Signal:
    timestamp: datetime
    symbol: str
    signal_type: SignalType
    strength: float = 1.0
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    quantity: Optional[int] = None
    order_type: OrderType = OrderType.MARKET
    product_type: ProductType = ProductType.DELIVERY
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_entry(self) -> bool:
        return self.signal_type in (SignalType.LONG, SignalType.SHORT)

    @property
    def risk_reward(self) -> Optional[float]:
        if self.entry_price and self.stop_loss and self.take_profit:
            risk = abs(self.entry_price - self.stop_loss)
            reward = abs(self.take_profit - self.entry_price)
            return reward / risk if risk > 0 else None
        return None


class BaseStrategy(abc.ABC):
    """
    Abstract base class for all Aram-TMS trading strategies.
    Subclasses MUST implement: generate_signals, get_parameters, validate_parameters
    """
    NAME: str = "BaseStrategy"
    VERSION: str = "1.0.0"
    CATEGORY: str = "generic"
    TIMEFRAME: str = "daily"
    UNIVERSE: str = "nifty50"
    DESCRIPTION: str = "Base strategy"

    def __init__(self, risk_per_trade: float = 0.01, stop_loss_pct: float = 0.03,
                 take_profit_pct: float = 0.06, **kwargs: Any) -> None:
        self.risk_per_trade = risk_per_trade
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self._warmup_period: int = 0

    @abc.abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """
        Generate buy/sell signals from OHLCV data.
        Returns Series of 1 (buy), 0 (hold), -1 (sell).
        CRITICAL: Always shift(1) before returning — prevents look-ahead bias.
        """
        ...

    @abc.abstractmethod
    def get_parameters(self) -> Dict[str, Any]: ...

    @abc.abstractmethod
    def validate_parameters(self) -> bool: ...

    def get_stop_loss(self, entry_price: float, signal: int, atr: float = 0.0) -> float:
        mult = 2.0
        if atr > 0:
            return entry_price - atr * mult if signal == 1 else entry_price + atr * mult
        return entry_price * (1 - self.stop_loss_pct) if signal == 1 else entry_price * (1 + self.stop_loss_pct)

    def get_take_profit(self, entry_price: float, signal: int, atr: float = 0.0) -> float:
        mult = 4.0
        if atr > 0:
            return entry_price + atr * mult if signal == 1 else entry_price - atr * mult
        return entry_price * (1 + self.take_profit_pct) if signal == 1 else entry_price * (1 - self.take_profit_pct)

    def get_position_size(self, portfolio_value: float, entry_price: float,
                          stop_loss_price: float) -> int:
        risk_amount = portfolio_value * self.risk_per_trade
        risk_per_share = abs(entry_price - stop_loss_price)
        if risk_per_share <= 0:
            risk_per_share = entry_price * 0.01
        return max(1, int(risk_amount / risk_per_share))

    def get_warmup_period(self) -> int:
        return self._warmup_period

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.NAME, "version": self.VERSION, "parameters": self.get_parameters()}

    def __repr__(self) -> str:
        p = ", ".join(f"{k}={v}" for k, v in self.get_parameters().items())
        return f"{self.NAME}({p})"


# ---- Strategy Registry ----
STRATEGY_REGISTRY: Dict[str, type] = {}


def register_strategy(cls: type) -> type:
    STRATEGY_REGISTRY[cls.NAME] = cls
    return cls


def get_strategy(name: str, **kwargs: Any) -> BaseStrategy:
    if name not in STRATEGY_REGISTRY:
        raise ValueError(f"Strategy '{name}' not found. Available: {list(STRATEGY_REGISTRY.keys())}")
    return STRATEGY_REGISTRY[name](**kwargs)


def list_strategies() -> List[Dict[str, str]]:
    return [{"name": c.NAME, "category": c.CATEGORY, "timeframe": c.TIMEFRAME,
             "universe": c.UNIVERSE} for c in STRATEGY_REGISTRY.values()]
