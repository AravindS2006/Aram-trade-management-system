"""Core event bus for forward/live pipelines."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class EventType(StrEnum):
    SIGNAL = "signal"
    ORDER_REQUEST = "order_request"
    ORDER_PLACED = "order_placed"
    ORDER_REJECTED = "order_rejected"
    ORDER_CLOSED = "order_closed"
    RISK_BREACH = "risk_breach"
    HEARTBEAT = "heartbeat"


@dataclass(slots=True)
class Event:
    event_type: EventType
    source: str
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class EventBus:
    """Simple in-process pub/sub event bus."""

    def __init__(self) -> None:
        self._handlers: dict[EventType, list[Callable[[Event], None]]] = defaultdict(list)

    def subscribe(self, event_type: EventType, handler: Callable[[Event], None]) -> None:
        self._handlers[event_type].append(handler)

    def emit(self, event: Event) -> None:
        for handler in self._handlers.get(event.event_type, []):
            handler(event)
