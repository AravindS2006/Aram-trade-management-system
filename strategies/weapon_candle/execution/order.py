"""Order dataclass for strategy lifecycle tracking."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Order:
    """Simple order container with partial-close accounting."""

    symbol: str
    direction: str
    qty: int
    entry_price: float
    stop_price: float
    target1: float
    target2: float
    entry_ts: datetime
    score: int
    status: str = "open"
    exit_price: float = 0.0
    exit_ts: datetime | None = None
    exit_reason: str = ""
    pnl: float = 0.0
    half_closed: bool = False
    breakeven: bool = False
    realized_pnl: float = 0.0

    @property
    def multiplier(self) -> int:
        """Return direction multiplier for pnl math."""
        return 1 if self.direction == "long" else -1

    def close_partial(self, price: float, qty_to_close: int) -> None:
        """Book realized pnl for a partial fill and reduce open quantity."""
        if qty_to_close <= 0:
            return
        qty_to_close = min(qty_to_close, self.qty)
        self.realized_pnl += (price - self.entry_price) * qty_to_close * self.multiplier
        self.qty -= qty_to_close

    def close(self, price: float, ts: datetime, reason: str) -> None:
        """Close any remaining quantity and finalize order pnl."""
        if self.qty > 0:
            self.realized_pnl += (price - self.entry_price) * self.qty * self.multiplier
            self.qty = 0
        self.exit_price = price
        self.exit_ts = ts
        self.exit_reason = reason
        self.status = "closed"
        self.pnl = self.realized_pnl
