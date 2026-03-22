"""Pre-trade guard filters."""

from __future__ import annotations

from datetime import date, time

from strategies.weapon_candle.config import WeaponCandleConfig
from strategies.weapon_candle.utils.time_filter import in_entry_session


def can_enter_now(ts_time: time, daily_trades: int, cfg: WeaponCandleConfig) -> bool:
    """Return True when time window and daily cap both allow entries."""
    return in_entry_session(ts_time, cfg) and (daily_trades < cfg.MAX_DAILY_TRADES)


def next_daily_counter(current_date: date | None, ts_date: date) -> tuple[date, int]:
    """Reset daily trade count on date rollover."""
    if current_date != ts_date:
        return ts_date, 0
    return ts_date, -1
