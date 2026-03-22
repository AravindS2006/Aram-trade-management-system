from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LiveTradingState:
    positions: list[dict[str, Any]] = field(default_factory=list)
    capital: float = 100000.0


def on_market_event(state: LiveTradingState, event: dict[str, Any]) -> LiveTradingState:
    """Placeholder event handler for broker-connected live trading."""
    _ = event
    return state
