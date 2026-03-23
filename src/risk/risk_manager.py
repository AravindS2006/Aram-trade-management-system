"""
Risk Manager - Aram-TMS
Pre-trade validation, portfolio risk monitoring, and circuit breakers.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import numpy as np
from loguru import logger


@dataclass
class RiskCheckResult:
    passed: bool
    reasons: List[str] = field(default_factory=list)
    def __bool__(self): return self.passed


@dataclass
class RiskConfig:
    max_capital_at_risk_daily: float = 0.02
    max_drawdown_stop: float = 0.15
    max_open_positions: int = 20
    max_sector_concentration: float = 0.30
    max_single_stock_pct: float = 0.05
    cash_buffer: float = 0.10
    default_risk_per_trade: float = 0.01
    max_risk_per_trade: float = 0.02
    min_rr_ratio: float = 2.0
    max_order_value: float = 500_000
    min_liquidity_multiple: float = 5.0
    daily_loss_limit: float = 0.03
    consecutive_loss_halt: int = 5
    max_orders_per_minute: int = 10


class RiskManager:
    """
    Institutional risk management for Aram-TMS.
    Every order must pass validate_order() before execution.
    """
    def __init__(self, config: Optional[RiskConfig] = None) -> None:
        self.config = config or RiskConfig()
        self._daily_pnl: float = 0.0
        self._consecutive_losses: int = 0
        self._orders_this_minute: int = 0
        self._last_minute_reset: datetime = datetime.now()
        self._circuit_breaker_active: bool = False
        self._ban_list: set = set()
        logger.info("RiskManager initialized")

    def validate_order(self, symbol: str, quantity: int, price: float, side: str,
                       portfolio_value: float, open_positions: int = 0,
                       sector: Optional[str] = None, sector_exposure: float = 0.0,
                       daily_volume: Optional[float] = None,
                       stop_loss: Optional[float] = None,
                       take_profit: Optional[float] = None) -> RiskCheckResult:
        """Run all pre-trade risk checks. Call before every order."""
        failures = []
        if self._circuit_breaker_active:
            return RiskCheckResult(False, ["Circuit breaker active"])
        if symbol.upper() in self._ban_list:
            failures.append(f"{symbol} on F&O ban list")
        order_value = quantity * price
        if order_value > self.config.max_order_value:
            failures.append(f"Order Rs.{order_value:,.0f} > limit Rs.{self.config.max_order_value:,.0f}")
        pct = order_value / portfolio_value if portfolio_value > 0 else 1.0
        if pct > self.config.max_single_stock_pct:
            failures.append(f"Position {pct:.1%} > {self.config.max_single_stock_pct:.1%}")
        if open_positions >= self.config.max_open_positions:
            failures.append(f"Max positions ({self.config.max_open_positions}) reached")
        if sector and (sector_exposure + pct) > self.config.max_sector_concentration:
            failures.append(f"Sector '{sector}' exposure {(sector_exposure+pct):.1%} > {self.config.max_sector_concentration:.1%}")
        if daily_volume and daily_volume > 0 and quantity > daily_volume / self.config.min_liquidity_multiple:
            failures.append(f"Order qty {quantity} > liquidity limit {daily_volume/self.config.min_liquidity_multiple:.0f}")
        if side.upper() == "BUY" and stop_loss is None:
            failures.append("Stop loss required for all buy orders")
        if stop_loss and take_profit and price > 0:
            risk = abs(price - stop_loss)
            reward = abs(take_profit - price)
            rr = reward / risk if risk > 0 else 0
            if rr < self.config.min_rr_ratio:
                failures.append(f"R:R {rr:.1f} < minimum {self.config.min_rr_ratio:.1f}")
        daily_loss_pct = abs(self._daily_pnl) / portfolio_value if self._daily_pnl < 0 and portfolio_value > 0 else 0
        if daily_loss_pct >= self.config.daily_loss_limit:
            self._circuit_breaker_active = True
            failures.append(f"Daily loss {daily_loss_pct:.1%} >= limit {self.config.daily_loss_limit:.1%}")
        self._tick_rate_limit()
        if self._orders_this_minute > self.config.max_orders_per_minute:
            failures.append(f"Rate limit {self._orders_this_minute}/min")
        result = RiskCheckResult(len(failures) == 0, failures)
        if not result.passed:
            logger.warning(f"Risk FAIL [{symbol}]: {failures}")
        return result

    def validate_portfolio_drawdown(self, portfolio_value: float, peak_value: float) -> RiskCheckResult:
        if peak_value <= 0: return RiskCheckResult(True)
        dd = (portfolio_value / peak_value) - 1
        if dd <= -self.config.max_drawdown_stop:
            self._circuit_breaker_active = True
            return RiskCheckResult(False, [f"Portfolio DD {dd:.1%} breached {-self.config.max_drawdown_stop:.1%} — CIRCUIT BREAKER"])
        return RiskCheckResult(True)

    def calculate_position_size(self, portfolio_value: float, entry_price: float,
                                stop_loss_price: float, method: str = "fixed_fractional",
                                win_rate: float = 0.5, avg_win_r: float = 2.0) -> int:
        if method == "fixed_fractional":
            risk = portfolio_value * self.config.default_risk_per_trade
            per_share = abs(entry_price - stop_loss_price)
            if per_share <= 0: return 0
            return max(0, int(risk / per_share))
        elif method == "kelly":
            b, p, q = avg_win_r, win_rate, 1-win_rate
            kelly = max(0, (b*p - q)/b) * 0.25
            return max(0, int(portfolio_value * kelly / entry_price))
        elif method == "equal_weight":
            return max(0, int(portfolio_value / self.config.max_open_positions / entry_price))
        return 0

    def record_trade_result(self, pnl: float) -> None:
        self._daily_pnl += pnl
        if pnl < 0:
            self._consecutive_losses += 1
        else:
            self._consecutive_losses = 0
        if self._consecutive_losses >= self.config.consecutive_loss_halt:
            self._circuit_breaker_active = True
            logger.warning(f"CIRCUIT BREAKER: {self._consecutive_losses} consecutive losses")

    def reset_daily_state(self) -> None:
        self._daily_pnl = 0.0; self._consecutive_losses = 0
        self._circuit_breaker_active = False; self._orders_this_minute = 0
        logger.info("Risk daily state reset")

    def update_ban_list(self, symbols: List[str]) -> None:
        self._ban_list = set(s.upper() for s in symbols)
        logger.info(f"F&O ban list updated: {len(self._ban_list)} symbols")

    def override_circuit_breaker(self, reason: str) -> None:
        logger.warning(f"Circuit breaker override: {reason}")
        self._circuit_breaker_active = False

    def _tick_rate_limit(self):
        now = datetime.now()
        if (now - self._last_minute_reset).total_seconds() >= 60:
            self._orders_this_minute = 0; self._last_minute_reset = now
        self._orders_this_minute += 1

    @property
    def is_halted(self) -> bool: return self._circuit_breaker_active

    def get_status(self) -> Dict[str, Any]:
        return {"circuit_breaker": self._circuit_breaker_active, "daily_pnl": self._daily_pnl,
                "consecutive_losses": self._consecutive_losses, "ban_list": len(self._ban_list)}
