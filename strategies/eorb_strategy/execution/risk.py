"""Risk management and position sizing for E-ORB strategy."""

from __future__ import annotations

from dataclasses import dataclass

from strategies.eorb_strategy.config import (
    ATR_SL_MULTIPLIER,
    CAPITAL,
    MAX_POSITION_PCT,
    RISK_PER_TRADE_PCT,
    SL_BUFFER_PCT,
    TARGET1_RR,
    TARGET2_RR,
)


@dataclass
class TargetLevels:
    target1: float
    target2: float
    risk: float


def calculate_stop(
    orb: dict,
    direction: str,
    entry_price: float,
    atr: float = 0.0,
) -> float:
    """Calculate stop-loss at opposite ORB edge with buffer.

    Uses whichever is TIGHTER to entry: ORB edge stop or ATR-based stop.
    """
    orb_high = orb["orb_high"]
    orb_low = orb["orb_low"]

    if direction == "long":
        orb_stop = orb_low * (1 - SL_BUFFER_PCT)
        atr_stop = entry_price - ATR_SL_MULTIPLIER * atr if atr > 0 else 0.0
        # Use tighter (closer to entry) stop
        if atr_stop > 0:
            return max(orb_stop, atr_stop)
        return orb_stop

    # Short
    orb_stop = orb_high * (1 + SL_BUFFER_PCT)
    atr_stop = entry_price + ATR_SL_MULTIPLIER * atr if atr > 0 else float("inf")
    return min(orb_stop, atr_stop)


def calculate_targets(
    entry_price: float,
    orb_range: float,
    direction: str,
    target1_rr: float = TARGET1_RR,
    target2_rr: float = TARGET2_RR,
) -> dict:
    """Calculate target levels based on ORB range width × RR multiple.

    Returns dict with target1, target2, risk.
    """
    if direction == "long":
        target1 = entry_price + orb_range * target1_rr
        target2 = entry_price + orb_range * target2_rr
    else:
        target1 = entry_price - orb_range * target1_rr
        target2 = entry_price - orb_range * target2_rr

    return TargetLevels(target1=target1, target2=target2, risk=orb_range).__dict__


def calculate_position_size(
    capital: float,
    entry_price: float,
    stop_price: float,
    size_multiplier: float = 1.0,
) -> int:
    """Risk-based position sizing: risk_amount / sl_distance, capped at 15% of capital.

    Parameters
    ----------
    capital : float
        Current available capital.
    entry_price : float
        Planned entry price.
    stop_price : float
        Stop-loss price.
    size_multiplier : float
        From scorer: 1.0 for full size, 0.5 for C-grade signals.

    Returns
    -------
    int : Number of shares/lots to trade.
    """
    risk_amount = capital * RISK_PER_TRADE_PCT * size_multiplier
    sl_distance = abs(entry_price - stop_price)
    if sl_distance <= 0:
        return 0

    raw_qty = int(risk_amount / sl_distance)
    max_qty = int(capital * MAX_POSITION_PCT / entry_price) if entry_price > 0 else 0
    return min(raw_qty, max_qty)
