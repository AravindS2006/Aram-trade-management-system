from __future__ import annotations

import pandas as pd


def layer2_check(df: pd.DataFrame, idx: int, direction: str) -> dict:
    """Layer 2: TK cross trigger with cloud and chikou confirmation."""
    if idx < 27:
        return {"pass": False, "score": 0, "entry_price": 0.0, "reason": "warmup"}

    row = df.iloc[idx]
    score = 0

    if direction == "long":
        if int(row.get("tk_cross_bull", 0)) != 1:
            return {"pass": False, "score": 0, "entry_price": 0.0, "reason": "missing_tk_cross_bull"}
        if int(row.get("above_cloud", 0)) != 1:
            return {"pass": False, "score": 0, "entry_price": 0.0, "reason": "cross_not_above_cloud"}
        score += 2
        if int(row.get("chikou_bull", 0)) == 1:
            score += 1
        if float(df["tenkan"].iloc[idx]) > float(df["tenkan"].iloc[idx - 1]):
            score += 1
    else:
        if int(row.get("tk_cross_bear", 0)) != 1:
            return {"pass": False, "score": 0, "entry_price": 0.0, "reason": "missing_tk_cross_bear"}
        if int(row.get("below_cloud", 0)) != 1:
            return {"pass": False, "score": 0, "entry_price": 0.0, "reason": "cross_not_below_cloud"}
        score += 2
        if int(row.get("chikou_bear", 0)) == 1:
            score += 1
        if float(df["tenkan"].iloc[idx]) < float(df["tenkan"].iloc[idx - 1]):
            score += 1

    entry_price = float(df["close"].iloc[idx])
    return {"pass": True, "score": score, "entry_price": entry_price, "reason": "layer2_pass"}
