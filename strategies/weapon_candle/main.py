"""Live bar-close orchestrator for Weapon Candle."""

from __future__ import annotations

from typing import Any

import pandas as pd

from strategies.weapon_candle.config import WeaponCandleConfig
from strategies.weapon_candle.execution.manager import manage_position
from strategies.weapon_candle.execution.order import Order
from strategies.weapon_candle.execution.risk import (
    calculate_qty,
    calculate_stop,
    calculate_targets,
)
from strategies.weapon_candle.indicators.pipeline import apply_all_indicators
from strategies.weapon_candle.signals.filters import can_enter_now
from strategies.weapon_candle.signals.scorer import score_signal, score_to_size_multiplier
from strategies.weapon_candle.utils.time_filter import is_hard_exit_time

State = dict[str, Any]


def _force_close_all(
    state: State, row: pd.Series, ts: pd.Timestamp, cfg: WeaponCandleConfig
) -> State:
    """Force close all open positions at hard exit."""
    updated_positions: list[Order] = []
    for order in state["positions"]:
        updated_positions.append(manage_position(order, row, ts, cfg))
    state["positions"] = [o for o in updated_positions if o.status == "open"]
    state.setdefault("closed", []).extend([o for o in updated_positions if o.status == "closed"])
    return state


def _next_entry_open(df_5m: pd.DataFrame) -> float | None:
    """Return next bar open if available in current frame."""
    if len(df_5m) < 2:
        return None
    return float(df_5m.iloc[-1]["open"])


def on_bar_close(df_5m: pd.DataFrame, state: State, cfg: WeaponCandleConfig) -> State:
    """Process a fully closed 5-minute bar and update state."""
    ts = df_5m.index[-1]
    row = df_5m.iloc[-1]

    if is_hard_exit_time(ts.time(), cfg):
        return _force_close_all(state, row, ts, cfg)

    managed_positions: list[Order] = []
    for order in state["positions"]:
        managed_positions.append(manage_position(order, row, ts, cfg))
    state["positions"] = [o for o in managed_positions if o.status == "open"]
    state.setdefault("closed", []).extend([o for o in managed_positions if o.status == "closed"])

    if not can_enter_now(ts.time(), int(state["daily_trades"]), cfg):
        return state

    df = apply_all_indicators(df_5m, cfg)
    latest = df.iloc[-1]
    if any(pd.isna(latest[k]) for k in cfg.SCORE_REQUIRED_COLUMNS):
        return state

    entry_open = _next_entry_open(df)
    if entry_open is None:
        return state

    for direction in ("long", "short"):
        score = score_signal(latest, direction, cfg)
        size_mult = score_to_size_multiplier(score, cfg)
        if size_mult <= 0:
            continue

        slippage = cfg.SLIPPAGE_PCT if direction == "long" else -cfg.SLIPPAGE_PCT
        entry = entry_open * (1.0 + slippage)
        stop = calculate_stop(entry, float(latest["atr"]), direction, cfg)
        t1, t2 = calculate_targets(entry, stop, direction, cfg)
        qty = calculate_qty(float(state["capital"]), entry, stop, cfg, size_mult=size_mult)
        if qty <= 0:
            continue

        order = Order(
            symbol=str(state.get("symbol", "SYM")),
            direction=direction,
            qty=qty,
            entry_price=entry,
            stop_price=stop,
            target1=t1,
            target2=t2,
            entry_ts=ts.to_pydatetime(),
            score=score,
        )
        state["positions"].append(order)
        state["daily_trades"] = int(state["daily_trades"]) + 1
        break

    return state
