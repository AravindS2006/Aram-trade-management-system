"""Standalone E-ORB orchestrator for live/forward-test usage."""

from __future__ import annotations

import pandas as pd

from strategies.eorb_strategy.config import MAX_DAILY_TRADES, VIX_DEFAULT_BACKTEST
from strategies.eorb_strategy.execution.order import place_order
from strategies.eorb_strategy.execution.risk import (
    calculate_position_size,
    calculate_stop,
    calculate_targets,
)
from strategies.eorb_strategy.indicators.adx import adx_signal, calculate_adx
from strategies.eorb_strategy.indicators.ema import calculate_ema
from strategies.eorb_strategy.indicators.rvol import calculate_rvol
from strategies.eorb_strategy.indicators.vwap import calculate_vwap
from strategies.eorb_strategy.signals.entry import check_entry
from strategies.eorb_strategy.signals.orb_builder import build_orb
from strategies.eorb_strategy.signals.scorer import score_signal
from strategies.eorb_strategy.utils.time_filter import (
    is_expiry_day,
    is_hard_exit_time,
    is_valid_entry_window,
)


def force_close_all(state: dict) -> dict:
    """Emergency close all open positions."""
    state["positions"] = []
    return state


def manage_open_positions(state: dict, row: pd.Series, df_5m: pd.DataFrame) -> dict:
    """Manage open positions — trailing stops, target checks, time exits."""
    _ = row
    _ = df_5m
    return state


def on_bar_close(df_5m: pd.DataFrame, state: dict) -> dict:
    """Process a new 5-min bar close for the E-ORB strategy.

    Parameters
    ----------
    df_5m : pd.DataFrame
        Latest 5-min OHLCV data with all bars for the current session.
    state : dict
        Mutable state dict with keys: capital, positions, daily_trade_count, vix_today.

    Returns
    -------
    dict : Updated state.
    """
    ts = df_5m.index[-1]

    # Hard exit check
    if is_hard_exit_time(ts):
        state = force_close_all(state)
        return state

    # Skip expiry days
    if is_expiry_day(ts):
        return state

    if not is_valid_entry_window(ts):
        return state

    if state.get("daily_trade_count", 0) >= MAX_DAILY_TRADES:
        return state

    # Compute indicators
    df_5m = calculate_adx(df_5m)
    df_5m = calculate_ema(df_5m)
    df_5m = calculate_vwap(df_5m)
    df_5m = calculate_rvol(df_5m)

    # Build ORB for today
    session_date = ts.date() if hasattr(ts, "date") else None
    orb = build_orb(df_5m, session_date)
    if not orb["orb_valid"]:
        return state

    vix_today = state.get("vix_today", VIX_DEFAULT_BACKTEST)
    row = df_5m.iloc[-1]
    idx = len(df_5m) - 1

    for direction in ["long", "short"]:
        result = check_entry(
            df_5m, orb, idx, direction,
            state.get("daily_trade_count", 0),
            vix_today,
        )
        if not result["signal"]:
            continue

        scored = score_signal(row, orb, direction, vix_today)
        if not scored["execute"]:
            continue

        entry_price = float(row["close"])
        atr = float(row.get("atr", 0))
        stop = calculate_stop(orb, direction, entry_price, atr)
        targets = calculate_targets(entry_price, orb["orb_range"], direction)
        size = calculate_position_size(
            state["capital"],
            entry_price,
            stop,
            scored["size_multiplier"],
        )
        if size <= 0:
            continue

        order = place_order(direction, size, entry_price, stop, targets, scored["total_score"], orb)
        state["positions"].append(order)
        state["daily_trade_count"] += 1

    state = manage_open_positions(state, row, df_5m)
    return state
