from __future__ import annotations

import pandas as pd


def layer1_check(row: pd.Series, direction: str) -> dict:
    """Layer 1: Cloud position filter with mandatory trend gate."""
    if int(row.get("inside_cloud", 0)) == 1:
        return {"pass": False, "score": 0, "reason": "price_inside_cloud"}

    score = 0
    if direction == "long":
        if float(row.get("close", 0)) < float(row.get("ema_200", 0)):
            return {"pass": False, "score": 0, "reason": "price_below_ema200"}
        if int(row.get("above_cloud", 0)) != 1:
            return {"pass": False, "score": 0, "reason": "price_in_or_below_cloud"}
        score += 2
        if int(row.get("cloud_bull", 0)) == 1:
            score += 1
        if str(row.get("volatility_regime", "")) == "trending":
            score += 1
        return {"pass": True, "score": score, "reason": "long_layer1_pass"}

    if float(row.get("close", 0)) > float(row.get("ema_200", 1e9)):
        return {"pass": False, "score": 0, "reason": "price_above_ema200"}
    if int(row.get("below_cloud", 0)) != 1:
        return {"pass": False, "score": 0, "reason": "price_in_or_above_cloud"}
    score += 2
    if int(row.get("cloud_bull", 1)) == 0:
        score += 1
    if str(row.get("volatility_regime", "")) == "trending":
        score += 1
    return {"pass": True, "score": score, "reason": "short_layer1_pass"}
