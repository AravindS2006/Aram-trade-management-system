from __future__ import annotations

from dataclasses import dataclass

from strategies.ichimoku_strategy.config import (
    ATR_SL_MULTIPLIER,
    RISK_PCT,
    RR_TARGET1,
    RR_TARGET2,
)


@dataclass
class TargetLevels:
    target1: float
    target2: float
    risk: float


def calculate_position_size(
    capital: float,
    entry_price: float,
    stop_price: float,
    size_multiplier: float,
) -> int:
    risk_amount = capital * RISK_PCT * size_multiplier
    risk_per_share = abs(entry_price - stop_price)
    if risk_per_share <= 0:
        return 0
    return int(risk_amount / risk_per_share)


def calculate_stop(row, direction: str, entry_price: float) -> float:
    kijun = float(row["kijun"])
    atr = float(row["atr"])
    senkou_a = float(row["senkou_a"])
    senkou_b = float(row["senkou_b"])

    if direction == "long":
        kijun_stop = kijun * (1 - 0.001)
        atr_stop = entry_price - ATR_SL_MULTIPLIER * atr
        cloud_stop = min(senkou_a, senkou_b) * (1 - 0.001)
        return max(kijun_stop, atr_stop, cloud_stop)

    kijun_stop = kijun * (1 + 0.001)
    atr_stop = entry_price + ATR_SL_MULTIPLIER * atr
    cloud_stop = max(senkou_a, senkou_b) * (1 + 0.001)
    return min(kijun_stop, atr_stop, cloud_stop)


def calculate_targets(entry: float, stop: float, direction: str) -> dict:
    risk = abs(entry - stop)
    if direction == "long":
        target1 = entry + risk * RR_TARGET1
        target2 = entry + risk * RR_TARGET2
    else:
        target1 = entry - risk * RR_TARGET1
        target2 = entry - risk * RR_TARGET2
    return TargetLevels(target1=target1, target2=target2, risk=risk).__dict__

