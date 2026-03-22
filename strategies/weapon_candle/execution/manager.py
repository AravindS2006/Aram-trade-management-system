"""Open-position management loop."""

from __future__ import annotations

import pandas as pd

from strategies.weapon_candle.config import WeaponCandleConfig
from strategies.weapon_candle.execution.order import Order
from strategies.weapon_candle.utils.time_filter import is_hard_exit_time


def _commission_cost(price: float, qty: int, cfg: WeaponCandleConfig) -> float:
    """Estimate two-sided commission for realized amount."""
    return price * qty * cfg.COMMISSION_PCT * 2.0


def manage_position(
    order: Order,
    row: pd.Series,
    ts: pd.Timestamp,
    cfg: WeaponCandleConfig,
) -> Order:
    """Manage one open order for stop/targets/trail/hard-exit in priority order."""
    if order.status != "open":
        return order

    high_v, low_v, close_v = float(row["high"]), float(row["low"]), float(row["close"])

    if is_hard_exit_time(ts.time(), cfg):
        remaining_qty = order.qty
        order.close(close_v, ts.to_pydatetime(), "hard_exit")
        order.pnl -= _commission_cost(close_v, remaining_qty, cfg)
        return order

    if order.direction == "long":
        if low_v <= order.stop_price:
            remaining_qty = order.qty
            order.close(order.stop_price, ts.to_pydatetime(), "stop_loss")
            order.pnl -= _commission_cost(order.stop_price, remaining_qty, cfg)
            return order

        if (not order.half_closed) and (high_v >= order.target1):
            qty_to_close = max(1, int(order.qty * cfg.T1_CLOSE_PCT))
            order.close_partial(order.target1, qty_to_close)
            order.half_closed = True
            order.breakeven = True
            order.stop_price = order.entry_price

        if high_v >= order.target2:
            remaining_qty = order.qty
            order.close(order.target2, ts.to_pydatetime(), "target2")
            order.pnl -= _commission_cost(order.target2, remaining_qty, cfg)
            return order

        if order.half_closed and not pd.isna(row["ema9"]) and close_v < float(row["ema9"]):
            remaining_qty = order.qty
            order.close(close_v, ts.to_pydatetime(), "ema_trail")
            order.pnl -= _commission_cost(close_v, remaining_qty, cfg)
            return order

    else:
        if high_v >= order.stop_price:
            remaining_qty = order.qty
            order.close(order.stop_price, ts.to_pydatetime(), "stop_loss")
            order.pnl -= _commission_cost(order.stop_price, remaining_qty, cfg)
            return order

        if (not order.half_closed) and (low_v <= order.target1):
            qty_to_close = max(1, int(order.qty * cfg.T1_CLOSE_PCT))
            order.close_partial(order.target1, qty_to_close)
            order.half_closed = True
            order.breakeven = True
            order.stop_price = order.entry_price

        if low_v <= order.target2:
            remaining_qty = order.qty
            order.close(order.target2, ts.to_pydatetime(), "target2")
            order.pnl -= _commission_cost(order.target2, remaining_qty, cfg)
            return order

        if order.half_closed and not pd.isna(row["ema9"]) and close_v > float(row["ema9"]):
            remaining_qty = order.qty
            order.close(close_v, ts.to_pydatetime(), "ema_trail")
            order.pnl -= _commission_cost(close_v, remaining_qty, cfg)
            return order

    return order
