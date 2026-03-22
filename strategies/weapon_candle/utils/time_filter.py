"""Session window and hard-exit helpers."""

from __future__ import annotations

from datetime import time

from strategies.weapon_candle.config import WeaponCandleConfig


def in_entry_session(ts_time: time, cfg: WeaponCandleConfig) -> bool:
    """Return True when timestamp is within allowed entry windows."""
    in_first = cfg.ENTRY_START <= ts_time <= cfg.ENTRY_END1
    in_second = cfg.ENTRY_START2 <= ts_time <= cfg.ENTRY_END2
    return in_first or in_second


def is_hard_exit_time(ts_time: time, cfg: WeaponCandleConfig) -> bool:
    """Return True at or after configured hard-exit time."""
    return ts_time >= cfg.HARD_EXIT
