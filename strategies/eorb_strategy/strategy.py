"""E-ORB strategy adapter for the existing BaseStrategy/IntradayBacktester framework.

This is the main strategy class that integrates all E-ORB components (ADX, EMA,
VWAP, RVOL, ORB builder, entry gates, scorer) and outputs -1/0/1 signals
compatible with the core backtester.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from core.strategy import BaseStrategy
from strategies.eorb_strategy.config import (
    ADX_MIN_THRESHOLD,
    MAX_DAILY_TRADES,
    ORB_BUFFER_PCT,
    RVOL_MIN,
    SCORE_C_MIN,
    VIX_DEFAULT_BACKTEST,
    VIX_MAX,
    VIX_MIN,
)
from strategies.eorb_strategy.indicators.adx import adx_signal, calculate_adx
from strategies.eorb_strategy.execution.risk import calculate_stop, calculate_targets
from strategies.eorb_strategy.indicators.ema import calculate_ema
from strategies.eorb_strategy.indicators.rvol import calculate_rvol
from strategies.eorb_strategy.indicators.vwap import calculate_vwap
from strategies.eorb_strategy.signals.orb_builder import build_orb
from strategies.eorb_strategy.signals.scorer import score_signal
from strategies.eorb_strategy.utils.time_filter import (
    is_expiry_day,
    is_hard_exit_time,
    is_valid_entry_window,
)


class EORBStrategy(BaseStrategy):
    """Enhanced Opening Range Breakout strategy adapter.

    Computes ADX, EMA 9/21, session-reset VWAP, and RVOL indicators, then
    scans for ORB breakouts with the full 6-step mandatory gate system.
    Outputs -1/0/1 signals for the IntradayBacktester.
    """

    def generate_indicators(self):
        out = self.data.copy()

        # Standardise column names to lowercase for indicator functions
        out.columns = [c.lower() for c in out.columns]

        # Ensure timezone-aware index
        if out.index.tz is None:
            out.index = out.index.tz_localize("Asia/Kolkata")

        # Compute indicators
        out = calculate_adx(out)
        out = calculate_ema(out)
        out = calculate_vwap(out)
        out = calculate_rvol(out)

        # Previous day high/low for scoring
        out["session_date_key"] = out.index.tz_convert("Asia/Kolkata").date
        day_groups = out.groupby("session_date_key")
        out["prev_day_high"] = day_groups["high"].transform("max").shift(1)
        out["prev_day_low"] = day_groups["low"].transform("min").shift(1)
        # Forward-fill so each intraday bar has prev day levels
        out["prev_day_high"] = out["prev_day_high"].ffill()
        out["prev_day_low"] = out["prev_day_low"].ffill()

        # Keep canonical OHLCV columns expected by IntradayBacktester
        out["Open"] = out["open"]
        out["High"] = out["high"]
        out["Low"] = out["low"]
        out["Close"] = out["close"]
        out["Volume"] = out["volume"]

        self.data = out
        self.signals = self.signals.reindex(self.data.index, fill_value=0)

    def generate_signals(self):
        self.signals["signal"] = 0
        self.signals["sl_price"] = np.nan
        self.signals["tp_price"] = np.nan

        vix_today = float(self.params.get("vix_today", VIX_DEFAULT_BACKTEST))
        max_daily_trades = int(self.params.get("max_daily_trades", MAX_DAILY_TRADES))
        min_score = int(self.params.get("min_signal_score", SCORE_C_MIN))
        allow_short = bool(self.params.get("allow_short", True))
        cooldown_bars = int(self.params.get("cooldown_bars", 3))

        trades_by_day: dict[object, int] = {}
        last_signal_bar = -10_000

        # Pre-check VIX
        if not (VIX_MIN <= vix_today <= VIX_MAX):
            return  # No trading today — VIX out of range

        # Build ORB for each unique session date
        orb_cache: dict[object, dict] = {}

        for i in range(1, len(self.data) - 1):
            row = self.data.iloc[i]
            ts = self.data.index[i]

            # Skip if ADX not yet available
            if np.isnan(row.get("adx", np.nan)):
                continue

            # Get session date
            session_day = ts.date() if hasattr(ts, "date") else None
            if session_day is None:
                continue

            # Skip expiry days
            if is_expiry_day(ts):
                continue

            # Build ORB for this day if not cached
            if session_day not in orb_cache:
                orb_cache[session_day] = build_orb(self.data, session_day)

            orb = orb_cache[session_day]

            # Skip if ORB invalid
            if not orb["orb_valid"]:
                continue

            # Check daily trade cap
            day_count = trades_by_day.get(session_day, 0)
            if day_count >= max_daily_trades:
                continue

            # Cooldown check
            if i - last_signal_bar < cooldown_bars:
                continue

            # Must be in entry window and not at hard exit
            if not is_valid_entry_window(ts):
                continue
            if is_hard_exit_time(ts):
                continue

            close = float(row["close"])
            orb_high = orb["orb_high"]
            orb_low = orb["orb_low"]

            final_direction = 0
            final_score = -1
            final_sl = np.nan
            final_tp = np.nan

            directions = ["long", "short"] if allow_short else ["long"]
            for direction in directions:
                # Gate 1: Breakout detection
                if direction == "long":
                    if close <= orb_high * (1 + ORB_BUFFER_PCT):
                        continue
                else:
                    if close >= orb_low * (1 - ORB_BUFFER_PCT):
                        continue

                # Gate 2: ADX gate
                if not adx_signal(row, direction):
                    continue

                # Gate 3: VWAP institutional gate
                vwap_val = float(row.get("vwap", 0))
                if direction == "long" and close <= vwap_val:
                    continue
                if direction == "short" and close >= vwap_val:
                    continue

                # Gate 4: RVOL gate
                rvol_val = float(row.get("rvol", 0))
                if rvol_val < RVOL_MIN:
                    continue

                # Score the signal
                pdh = float(row.get("prev_day_high", 0))
                pdl = float(row.get("prev_day_low", 0))
                scored = score_signal(row, orb, direction, vix_today, pdh, pdl)

                if not scored["execute"]:
                    continue

                if scored["total_score"] < min_score:
                    continue

                if scored["total_score"] > final_score:
                    final_score = scored["total_score"]
                    final_direction = 1 if direction == "long" else -1
                    atr_val = float(row.get("atr", 0.0))
                    
                    final_sl = calculate_stop(orb, direction, close, atr_val)
                    
                    # Use Target 1 or Target 2 based on score multiplier logic
                    targets = calculate_targets(
                        close, orb["orb_range"], direction, 
                        target1_rr=scored["adjusted_target_rr"]
                    )
                    final_tp = targets["target1"]

            col_signal = self.signals.columns.get_loc("signal")
            col_sl = self.signals.columns.get_loc("sl_price")
            col_tp = self.signals.columns.get_loc("tp_price")
            
            self.signals.iloc[i, col_signal] = final_direction  # pyright: ignore[reportArgumentType]
            if final_direction != 0:
                self.signals.iloc[i, col_sl] = final_sl  # pyright: ignore[reportArgumentType]
                self.signals.iloc[i, col_tp] = final_tp  # pyright: ignore[reportArgumentType]
                
                last_signal_bar = i
                if session_day is not None:
                    trades_by_day[session_day] = trades_by_day.get(session_day, 0) + 1
