"""Risk sizing and target helpers."""

from __future__ import annotations

from strategies.weapon_candle.config import WeaponCandleConfig


def calculate_stop(entry: float, atr: float, direction: str, cfg: WeaponCandleConfig) -> float:
    """Calculate ATR-based stop with minimum absolute distance."""
    sl_dist = max(cfg.ATR_SL_MULT * atr, entry * cfg.MIN_SL_PCT)
    if direction == "long":
        return entry - sl_dist
    if direction == "short":
        return entry + sl_dist
    raise ValueError(f"Unknown direction: {direction}")


def calculate_targets(
    entry: float,
    stop: float,
    direction: str,
    cfg: WeaponCandleConfig,
) -> tuple[float, float]:
    """Return (target1, target2) from configured RR multiples."""
    risk = abs(entry - stop)
    if direction == "long":
        return entry + (risk * cfg.RR1), entry + (risk * cfg.RR2)
    if direction == "short":
        return entry - (risk * cfg.RR1), entry - (risk * cfg.RR2)
    raise ValueError(f"Unknown direction: {direction}")


def calculate_qty(
    capital: float,
    entry: float,
    stop: float,
    cfg: WeaponCandleConfig,
    size_mult: float = 1.0,
) -> int:
    """Size position by risk-per-trade, capped by notional allocation."""
    sl_distance = abs(entry - stop)
    if sl_distance <= 0:
        return 0

    risk_amount = capital * cfg.RISK_PCT * size_mult
    raw_qty = int(risk_amount / sl_distance)
    max_qty = int((capital * cfg.POSITION_CAPITAL_LIMIT_PCT) / entry)
    return max(1, min(raw_qty, max_qty))
