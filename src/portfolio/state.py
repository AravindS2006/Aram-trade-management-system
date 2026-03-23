"""Portfolio state cache for forward/live runs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pandas as pd


@dataclass(slots=True)
class PositionState:
    symbol: str
    quantity: int
    average_price: float
    unrealized_pnl: float = 0.0


class PortfolioState:
    def __init__(self) -> None:
        self.positions: dict[str, PositionState] = {}
        self.last_updated: datetime | None = None

    def sync_from_positions_df(self, positions: pd.DataFrame) -> None:
        next_positions: dict[str, PositionState] = {}
        if not positions.empty:
            for _, row in positions.iterrows():
                symbol = str(row.get("tradingSymbol", "")).upper()
                if not symbol:
                    continue
                qty = int(float(row.get("netQty", 0) or 0))
                if qty == 0:
                    continue
                avg_price = float(row.get("avgPrice", row.get("buyAvg", 0)) or 0)
                upnl = float(row.get("unrealizedProfit", row.get("pnl", 0)) or 0)
                next_positions[symbol] = PositionState(
                    symbol=symbol,
                    quantity=qty,
                    average_price=avg_price,
                    unrealized_pnl=upnl,
                )
        self.positions = next_positions
        self.last_updated = datetime.now()

    def has_position(self, symbol: str) -> bool:
        return symbol.upper() in self.positions

    def get_position_qty(self, symbol: str) -> int:
        pos = self.positions.get(symbol.upper())
        return pos.quantity if pos else 0

    def total_unrealized_pnl(self) -> float:
        return sum(p.unrealized_pnl for p in self.positions.values())

    def as_dict(self) -> dict[str, Any]:
        return {
            "position_count": len(self.positions),
            "symbols": sorted(self.positions.keys()),
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "unrealized_pnl": self.total_unrealized_pnl(),
        }
