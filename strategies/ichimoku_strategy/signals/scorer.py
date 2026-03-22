from __future__ import annotations

from strategies.ichimoku_strategy.config import HALF_SIZE_SCORE, MIN_SIGNAL_SCORE


def score_signal(l1: dict, l2: dict, l3: dict) -> dict:
    total = int(l1.get("score", 0) + l2.get("score", 0) + l3.get("score", 0))
    if total >= 8:
        grade = "A"
    elif total >= 5:
        grade = "B"
    elif total >= 3:
        grade = "C"
    else:
        grade = "skip"

    if total >= MIN_SIGNAL_SCORE:
        size_multiplier = 1.0
    elif total >= HALF_SIZE_SCORE:
        size_multiplier = 0.5
    else:
        size_multiplier = 0.0

    return {
        "total_score": total,
        "execute": total >= HALF_SIZE_SCORE,
        "size_multiplier": size_multiplier,
        "grade": grade,
    }

