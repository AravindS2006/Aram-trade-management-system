from __future__ import annotations

from datetime import datetime


def place_order(direction: str, size: int, entry_price: float, stop: float, targets: dict) -> dict:
    return {
        "direction": direction,
        "size": size,
        "entry_price": float(entry_price),
        "stop": float(stop),
        "targets": targets,
        "created_at": datetime.utcnow().isoformat(),
        "status": "open",
    }

