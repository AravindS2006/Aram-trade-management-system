"""OHLCV validation helpers for data ingestion."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)


def validate_ohlcv(df: pd.DataFrame, max_gap_days: int = 5) -> ValidationResult:
    if df.empty:
        return ValidationResult(False, ["Empty dataset"])

    errors: list[str] = []
    required = ["Open", "High", "Low", "Close", "Volume"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        errors.append(f"Missing columns: {missing}")
        return ValidationResult(False, errors)

    if (df["High"] < df["Low"]).any():
        errors.append("High < Low rows detected")

    if (df["Close"] <= 0).any():
        errors.append("Non-positive close detected")

    if (df["Volume"] < 0).any():
        errors.append("Negative volume detected")

    if len(df.index) > 1:
        max_gap = df.index.to_series().diff().dropna().max()
        if pd.notna(max_gap) and max_gap > pd.Timedelta(days=max_gap_days):
            errors.append(f"Data gap exceeds {max_gap_days} days: {max_gap}")

    return ValidationResult(len(errors) == 0, errors)
