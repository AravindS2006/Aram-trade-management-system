"""Bar-by-bar backtest engine for E-ORB strategy."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from strategies.eorb_strategy.backtest.metrics import compute_metrics
from strategies.eorb_strategy.execution.risk import calculate_position_size, calculate_stop, calculate_targets


@dataclass
class BacktestResult:
    trades: pd.DataFrame
    equity_curve: pd.Series
    metrics: dict


def run_backtest(
    df: pd.DataFrame,
    initial_capital: float = 500_000,
    commission: float = 0.0003,
    slippage_pct: float = 0.0002,
) -> BacktestResult:
    """Simulate E-ORB strategy bar-by-bar.

    Returns BacktestResult with trades list and equity curve.
    The DataFrame is expected to already contain all indicators and signal columns.
    """
    cash = initial_capital
    position = 0
    entry_price = 0.0
    stop_price = 0.0
    target1 = 0.0
    target2 = 0.0
    t1_hit = False
    remaining_qty = 0
    full_qty = 0
    trailing_stop = 0.0
    trades: list[dict] = []
    equity: list[float] = []

    for i, row in enumerate(df.itertuples()):
        signal = int(row.signal) if hasattr(row, "signal") else 0
        close = float(row.close)
        high = float(row.high)
        low = float(row.low)
        atr_val = float(row.atr) if hasattr(row, "atr") else 0.0
        ema_fast_val = float(row.ema_fast) if hasattr(row, "ema_fast") else close

        # ── Position management ──
        if position != 0:
            exit_triggered = False
            exit_price = 0.0
            exit_reason = ""

            # 1. Check Stop-Loss
            if position == 1 and low <= stop_price:
                exit_price = stop_price * (1 - slippage_pct)
                exit_triggered = True
                exit_reason = "SL_HIT"
            elif position == -1 and high >= stop_price:
                exit_price = stop_price * (1 + slippage_pct)
                exit_triggered = True
                exit_reason = "SL_HIT"

            if not exit_triggered and not t1_hit:
                # 2. Check Target 1
                if position == 1 and high >= target1:
                    # Close 50% at T1
                    partial_qty = full_qty - remaining_qty  # already closed
                    t1_close_qty = int(full_qty * 0.5)
                    if t1_close_qty > 0:
                        pnl = (target1 * (1 - slippage_pct) - entry_price) * t1_close_qty
                        pnl -= t1_close_qty * target1 * commission * 2
                        cash += pnl
                        trades.append({
                            "bar": i,
                            "entry_price": entry_price,
                            "exit_price": round(target1, 2),
                            "qty": t1_close_qty,
                            "pnl": pnl,
                            "exit_reason": "TARGET1",
                            "direction": "long",
                        })
                        remaining_qty = full_qty - t1_close_qty
                        stop_price = entry_price  # Move to breakeven
                        trailing_stop = ema_fast_val * (1 - 0.002)
                        t1_hit = True
                elif position == -1 and low <= target1:
                    t1_close_qty = int(full_qty * 0.5)
                    if t1_close_qty > 0:
                        pnl = (entry_price - target1 * (1 + slippage_pct)) * t1_close_qty
                        pnl -= t1_close_qty * target1 * commission * 2
                        cash += pnl
                        trades.append({
                            "bar": i,
                            "entry_price": entry_price,
                            "exit_price": round(target1, 2),
                            "qty": t1_close_qty,
                            "pnl": pnl,
                            "exit_reason": "TARGET1",
                            "direction": "short",
                        })
                        remaining_qty = full_qty - t1_close_qty
                        stop_price = entry_price
                        trailing_stop = ema_fast_val * (1 + 0.002)
                        t1_hit = True

            if not exit_triggered and t1_hit and remaining_qty > 0:
                # 3. Trail remaining position using EMA9
                if position == 1:
                    new_trail = ema_fast_val * (1 - 0.002)
                    trailing_stop = max(trailing_stop, new_trail)
                    if low <= trailing_stop:
                        exit_price = trailing_stop * (1 - slippage_pct)
                        exit_triggered = True
                        exit_reason = "TRAIL_STOP"
                elif position == -1:
                    new_trail = ema_fast_val * (1 + 0.002)
                    trailing_stop = min(trailing_stop, new_trail)
                    if high >= trailing_stop:
                        exit_price = trailing_stop * (1 + slippage_pct)
                        exit_triggered = True
                        exit_reason = "TRAIL_STOP"

                # 4. Check Target 2
                if not exit_triggered:
                    if position == 1 and high >= target2:
                        exit_price = target2 * (1 - slippage_pct)
                        exit_triggered = True
                        exit_reason = "TARGET2"
                    elif position == -1 and low <= target2:
                        exit_price = target2 * (1 + slippage_pct)
                        exit_triggered = True
                        exit_reason = "TARGET2"

            if exit_triggered:
                qty_to_close = remaining_qty if t1_hit else full_qty
                if qty_to_close > 0:
                    if position == 1:
                        pnl = (exit_price - entry_price) * qty_to_close
                    else:
                        pnl = (entry_price - exit_price) * qty_to_close
                    pnl -= qty_to_close * exit_price * commission * 2
                    cash += pnl
                    trades.append({
                        "bar": i,
                        "entry_price": entry_price,
                        "exit_price": round(exit_price, 2),
                        "qty": qty_to_close,
                        "pnl": pnl,
                        "exit_reason": exit_reason,
                        "direction": "long" if position == 1 else "short",
                    })
                position = 0
                remaining_qty = 0
                full_qty = 0
                t1_hit = False

        # ── New Entry ──
        elif signal != 0 and atr_val > 0:
            sl = close - 1.5 * atr_val if signal == 1 else close + 1.5 * atr_val
            size = calculate_position_size(cash, close, sl, 1.0)
            if size > 0:
                entry_price = close * (1 + slippage_pct) if signal == 1 else close * (1 - slippage_pct)
                position = signal
                full_qty = size
                remaining_qty = size
                t1_hit = False

                orb_range_approx = atr_val * 2  # Approximation for engine
                if signal == 1:
                    stop_price = entry_price - 1.5 * atr_val
                    target1 = entry_price + orb_range_approx * 1.5
                    target2 = entry_price + orb_range_approx * 2.5
                else:
                    stop_price = entry_price + 1.5 * atr_val
                    target1 = entry_price - orb_range_approx * 1.5
                    target2 = entry_price - orb_range_approx * 2.5

                trailing_stop = 0.0
                cash -= size * entry_price * commission

        equity.append(cash + (remaining_qty if position != 0 else 0) * close * (1 if position == 1 else -1))

    equity_curve = pd.Series(equity, index=df.index)
    returns = equity_curve.pct_change().dropna()
    trades_df = pd.DataFrame(trades)
    metrics = compute_metrics(equity_curve, returns, trades_df)
    return BacktestResult(trades=trades_df, equity_curve=equity_curve, metrics=metrics)
