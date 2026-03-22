from __future__ import annotations

from datetime import datetime

import pandas as pd
import pytz

from strategies.ichimoku_strategy.config import (
    HARD_EXIT_TIME,
    LUNCH_END,
    LUNCH_START,
    SESSION1_END,
    SESSION1_START,
    SESSION2_END,
    SESSION2_START,
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


def is_valid_session(ts: pd.Timestamp | datetime) -> bool:
    """Return True when timestamp is inside active trading session windows."""
    t = _to_ist(ts).time()
    in_window_1 = SESSION1_START <= t < SESSION1_END
    in_window_2 = SESSION2_START <= t < SESSION2_END
    in_lunch = LUNCH_START <= t < LUNCH_END
    return (in_window_1 or in_window_2) and not in_lunch


def is_hard_exit(ts: pd.Timestamp | datetime) -> bool:
    """Return True once timestamp reaches or passes mandatory hard-exit time."""
    return _to_ist(ts).time() >= HARD_EXIT_TIME


def is_hard_exit_time(ts: pd.Timestamp | datetime) -> bool:
    """Backward-compatible alias for hard exit check."""
    return is_hard_exit(ts)


def session_minutes_remaining(ts: pd.Timestamp | datetime) -> int:
    """Return remaining minutes in current session window or 0 if outside session."""
    t_ist = _to_ist(ts)
    t = t_ist.time()

    if SESSION1_START <= t < SESSION1_END:
        end = t_ist.replace(hour=SESSION1_END.hour, minute=SESSION1_END.minute, second=0, microsecond=0)
    elif SESSION2_START <= t < SESSION2_END:
        end = t_ist.replace(hour=SESSION2_END.hour, minute=SESSION2_END.minute, second=0, microsecond=0)
    else:
        return 0

    return max(0, int((end - t_ist).total_seconds() // 60))

