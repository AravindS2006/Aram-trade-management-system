"""Bar-by-bar backtest engine for Weapon Candle."""

from __future__ import annotations

from collections import defaultdict

import pandas as pd

from strategies.weapon_candle.config import WeaponCandleConfig
from strategies.weapon_candle.execution.manager import manage_position
from strategies.weapon_candle.execution.order import Order
from strategies.weapon_candle.execution.risk import calculate_qty, calculate_stop, calculate_targets
from strategies.weapon_candle.signals.scorer import score_signal, score_to_size_multiplier
from strategies.weapon_candle.utils.time_filter import in_entry_session, is_hard_exit_time


def simulate_trade(
    df: pd.DataFrame,
    start_idx: int,
    order: Order,
    cfg: WeaponCandleConfig,
) -> tuple[float, str, pd.Timestamp]:
    """Simulate a single trade forward until closure and return pnl metadata."""
    for j in range(start_idx, len(df)):
        ts = df.index[j]
        row = df.iloc[j]
        order = manage_position(order, row, ts, cfg)
        if order.status == "closed":
            return order.pnl, order.exit_reason, ts
        if is_hard_exit_time(ts.time(), cfg):
            break

    final_ts = df.index[min(len(df) - 1, max(start_idx, 0))]
    return order.pnl, "open", final_ts


def run_backtest(df: pd.DataFrame, cfg: WeaponCandleConfig) -> dict[str, object]:
    """Run bar-by-bar backtest and return trades plus equity curve."""
    warmup = cfg.MACD_SLOW + cfg.BB_PERIOD + 10
    trades: list[dict[str, object]] = []
    equity_curve: list[float] = [cfg.CAPITAL]
    daily_count: dict[object, int] = defaultdict(int)
    capital = cfg.CAPITAL

    for i in range(warmup, len(df) - 1):
        ts = df.index[i]
        row = df.iloc[i]

        if not in_entry_session(ts.time(), cfg):
            continue

        trade_day = ts.date()
        if daily_count[trade_day] >= cfg.MAX_DAILY_TRADES:
            continue

        if any(pd.isna(row[k]) for k in cfg.SCORE_REQUIRED_COLUMNS):
            continue

        entry_ts = df.index[i + 1]
        entry_open = float(df.iloc[i + 1]["open"])

        opened = False
        for direction in ("long", "short"):
            score = score_signal(row, direction, cfg)
            size_mult = score_to_size_multiplier(score, cfg)
            if size_mult <= 0:
                continue

            slippage = cfg.SLIPPAGE_PCT if direction == "long" else -cfg.SLIPPAGE_PCT
            entry = entry_open * (1.0 + slippage)
            stop = calculate_stop(entry, float(row["atr"]), direction, cfg)
            t1, t2 = calculate_targets(entry, stop, direction, cfg)
            qty = calculate_qty(capital, entry, stop, cfg, size_mult=size_mult)
            if qty <= 0:
                continue

            order = Order(
                symbol="SYM",
                direction=direction,
                qty=qty,
                entry_price=entry,
                stop_price=stop,
                target1=t1,
                target2=t2,
                entry_ts=entry_ts.to_pydatetime(),
                score=score,
            )
            pnl, reason, exit_ts = simulate_trade(df, i + 1, order, cfg)
            pnl = max(pnl, -(capital * cfg.MAX_TRADE_LOSS))
            capital += pnl
            equity_curve.append(capital)

            trades.append(
                {
                    "entry_ts": entry_ts,
                    "exit_ts": exit_ts,
                    "direction": direction,
                    "entry": entry,
                    "stop": stop,
                    "qty": qty,
                    "score": score,
                    "pnl": pnl,
                    "reason": reason,
                }
            )
            daily_count[trade_day] += 1
            opened = True
            break

        if opened and is_hard_exit_time(ts.time(), cfg):
            continue

    return {"trades": trades, "equity_curve": equity_curve}
