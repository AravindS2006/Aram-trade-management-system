"""Order placement for E-ORB strategy."""

from __future__ import annotations

from datetime import datetime


def place_order(
    direction: str,
    size: int,
    entry_price: float,
    stop: float,
    targets: dict,
    signal_score: int = 0,
    orb: dict | None = None,
) -> dict:
    """Create an order dict with full trade metadata."""
    return {
        "direction": direction,
        "size": size,
        "entry_price": float(entry_price),
        "stop": float(stop),
        "targets": targets,
        "signal_score": signal_score,
        "orb_high": float(orb["orb_high"]) if orb else 0.0,
        "orb_low": float(orb["orb_low"]) if orb else 0.0,
        "orb_range": float(orb["orb_range"]) if orb else 0.0,
        "created_at": datetime.utcnow().isoformat(),
        "status": "open",
    }
