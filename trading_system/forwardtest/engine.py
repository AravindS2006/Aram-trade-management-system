from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ForwardTestState:
    positions: list[dict[str, Any]] = field(default_factory=list)
    daily_trade_count: int = 0
    capital: float = 100000.0


def on_new_bar(state: ForwardTestState, bar: dict[str, Any]) -> ForwardTestState:
    """Placeholder event loop for paper/forward testing integration."""
    _ = bar
    return state
