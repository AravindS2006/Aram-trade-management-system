from __future__ import annotations

import pandas as pd

from strategies.ichimoku_strategy.config import MAX_DAILY_TRADES
from strategies.ichimoku_strategy.data.preprocessor import preprocess
from strategies.ichimoku_strategy.execution.order import place_order
from strategies.ichimoku_strategy.execution.risk import (
    calculate_position_size,
    calculate_stop,
    calculate_targets,
)
from strategies.ichimoku_strategy.indicators.atr import calculate_atr
from strategies.ichimoku_strategy.indicators.ema import calculate_ema, confirm_micro_entry
from strategies.ichimoku_strategy.indicators.ichimoku import calculate_ichimoku
from strategies.ichimoku_strategy.indicators.rsi import calculate_rsi
from strategies.ichimoku_strategy.signals.layer1 import layer1_check
from strategies.ichimoku_strategy.signals.layer2 import layer2_check
from strategies.ichimoku_strategy.signals.layer3 import layer3_check
from strategies.ichimoku_strategy.signals.scorer import score_signal
from strategies.ichimoku_strategy.utils.logger import log_trade
from strategies.ichimoku_strategy.utils.time_filter import is_hard_exit_time, is_valid_session


def force_close_all(state: dict) -> dict:
    state["positions"] = []
    return state


def manage_open_positions(state: dict, row: pd.Series, df_5m: pd.DataFrame) -> dict:
    _ = row
    _ = df_5m
    return state


def on_bar_close(df_5m: pd.DataFrame, df_1m: pd.DataFrame, state: dict) -> dict:
    if not is_valid_session(df_5m.index[-1]):
        return state

    if state.get("daily_trade_count", 0) >= MAX_DAILY_TRADES:
        return state

    df_5m = calculate_ichimoku(df_5m)
    df_5m = calculate_rsi(df_5m)
    df_5m = calculate_atr(df_5m)
    df_5m = preprocess(df_5m)
    df_5m["vol_ma20"] = df_5m["volume"].rolling(20).mean()

    df_1m = calculate_ema(df_1m)
    row = df_5m.iloc[-1]

    for direction in ["long", "short"]:
        l1 = layer1_check(row, direction)
        if not l1["pass"]:
            continue

        l2 = layer2_check(df_5m, len(df_5m) - 1, direction)
        if not l2["pass"]:
            continue

        l3 = layer3_check(row, direction)
        signal = score_signal(l1, l2, l3)
        if not signal["execute"]:
            continue

        if not confirm_micro_entry(df_1m, direction):
            continue

        stop = calculate_stop(row, direction, l2["entry_price"])
        targets = calculate_targets(l2["entry_price"], stop, direction)
        size = calculate_position_size(
            state["capital"],
            l2["entry_price"],
            stop,
            signal["size_multiplier"],
        )
        if size <= 0:
            continue

        order = place_order(direction, size, l2["entry_price"], stop, targets)
        state["positions"].append(order)
        state["daily_trade_count"] += 1
        log_trade(signal, order)

    state = manage_open_positions(state, row, df_5m)
    if is_hard_exit_time(df_5m.index[-1]):
        state = force_close_all(state)

    return state

