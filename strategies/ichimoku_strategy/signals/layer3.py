from __future__ import annotations

import pandas as pd


def layer3_check(row: pd.Series, direction: str) -> dict:
    """Layer 3: RSI, VWAP, and volume confluence scoring."""
    score = 0
    vol_ma20 = float(row.get("vol_ma20", row.get("volume_ma20", 0.0)))
    volume_ok = bool(vol_ma20 > 0 and float(row["volume"]) > 1.2 * vol_ma20)

    macd_hist = float(row.get("macd_hist", 0.0))
    macd_val = float(row.get("macd", 0.0))

    if direction == "long":
        rsi_ok = bool(50.0 <= float(row["rsi"]) <= 85.0)
        vwap_ok = bool(float(row["close"]) > float(row["vwap"]))
        macd_ok = bool(macd_hist > 0 and macd_val > 0)
    else:
        rsi_ok = bool(15.0 <= float(row["rsi"]) <= 50.0)
        vwap_ok = bool(float(row["close"]) < float(row["vwap"]))
        macd_ok = bool(macd_hist < 0 and macd_val < 0)

    score += int(rsi_ok)
    score += int(vwap_ok)
    score += int(volume_ok)
    score += int(macd_ok)
    return {"score": score, "rsi_ok": rsi_ok, "vwap_ok": vwap_ok, "volume_ok": volume_ok, "macd_ok": macd_ok}
