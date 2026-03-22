"""Time and session filters for E-ORB strategy."""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import pytz

from strategies.eorb_strategy.config import (
    AVOID_EXPIRY_DAY,
    ENTRY_WINDOW_END,
    ENTRY_WINDOW_START,
    HARD_EXIT_TIME,
    LATE_ENTRY_CUTOFF,
    LATE_EXIT_TIME,
    LUNCH_BLACKOUT_END,
    LUNCH_BLACKOUT_START,
)

IST = pytz.timezone("Asia/Kolkata")


def _to_ist(ts: datetime | pd.Timestamp) -> datetime:
    """Convert any timestamp to timezone-aware IST datetime."""
    t = pd.Timestamp(ts)
    if t.tzinfo is None:
        t = t.tz_localize(IST)
    else:
        t = t.tz_convert(IST)
    return t.to_pydatetime()


def is_valid_entry_window(ts: pd.Timestamp | datetime) -> bool:
    """Return True when timestamp is inside the allowed entry window (09:30–14:00 IST).

    Also returns False during lunch blackout (11:30–13:00) as per known failure modes.
    """
    t = _to_ist(ts).time()
    if t < ENTRY_WINDOW_START or t >= ENTRY_WINDOW_END:
        return False
    # Lunch blackout — low liquidity period
    if LUNCH_BLACKOUT_START <= t < LUNCH_BLACKOUT_END:
        return False
    return True


def is_hard_exit_time(ts: pd.Timestamp | datetime) -> bool:
    """Return True once timestamp reaches or passes 15:15 IST."""
    return _to_ist(ts).time() >= HARD_EXIT_TIME


def is_expiry_day(ts: pd.Timestamp | datetime) -> bool:
    """Return True on Thursdays (weekly F&O expiry) when blackout is enabled."""
    if not AVOID_EXPIRY_DAY:
        return False
    return _to_ist(ts).weekday() == 3  # Thursday


def is_late_entry(ts: pd.Timestamp | datetime) -> bool:
    """Return True if the position was entered after the late entry cutoff (13:30 IST)."""
    return _to_ist(ts).time() >= LATE_ENTRY_CUTOFF


def should_close_late_entry(ts: pd.Timestamp | datetime) -> bool:
    """Return True if time >= 14:30 — used for early close of late entries when profitable."""
    return _to_ist(ts).time() >= LATE_EXIT_TIME
