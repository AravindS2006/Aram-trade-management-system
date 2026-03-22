from __future__ import annotations

import numpy as np

from core.strategy import BaseStrategy
from strategies.ichimoku_strategy.config import MAX_DAILY_TRADES, MIN_SIGNAL_SCORE
from strategies.ichimoku_strategy.data.preprocessor import preprocess
from strategies.ichimoku_strategy.indicators.atr import calculate_atr
from strategies.ichimoku_strategy.indicators.ichimoku import calculate_ichimoku
from strategies.ichimoku_strategy.indicators.rsi import calculate_rsi
from strategies.ichimoku_strategy.signals.layer1 import layer1_check
from strategies.ichimoku_strategy.signals.layer2 import layer2_check
from strategies.ichimoku_strategy.signals.layer3 import layer3_check
from strategies.ichimoku_strategy.signals.scorer import score_signal


class IchimokuRSIVWAPStrategy(BaseStrategy):
    """Ichimoku + RSI + VWAP + ATR strategy adapter for the existing backtester."""

    def generate_indicators(self):
        out = self.data.copy()
        out.columns = [c.lower() for c in out.columns]
        out = preprocess(out)
        out = calculate_ichimoku(out)
        out = calculate_rsi(out)
        out = calculate_atr(out)
        
        # Add MACD and ADX style filters (using simple EMA fast-slow diff for MACD proxy)
        out["ema_12"] = out["close"].ewm(span=12, adjust=False).mean()
        out["ema_26"] = out["close"].ewm(span=26, adjust=False).mean()
        out["macd"] = out["ema_12"] - out["ema_26"]
        out["macd_signal"] = out["macd"].ewm(span=9, adjust=False).mean()
        out["macd_hist"] = out["macd"] - out["macd_signal"]
        out["ema_200"] = out["close"].ewm(span=200, adjust=False).mean()

        out["vol_ma20"] = out["volume"].rolling(20).mean()

        # Keep canonical OHLCV columns expected by IntradayBacktester.
        out["Open"] = out["open"]
        out["High"] = out["high"]
        out["Low"] = out["low"]
        out["Close"] = out["close"]
        out["Volume"] = out["volume"]

        self.data = out
        self.signals = self.signals.reindex(self.data.index, fill_value=0)

    def generate_signals(self):
        self.signals["signal"] = 0

        cooldown_bars = int(self.params.get("cooldown_bars", 3))
        min_score = int(self.params.get("min_signal_score", MIN_SIGNAL_SCORE))
        max_daily_trades = int(self.params.get("max_daily_trades", MAX_DAILY_TRADES))
        allow_short = bool(self.params.get("allow_short", True))

        trades_by_day: dict[object, int] = {}
        last_signal_bar = -10_000

        for i in range(1, len(self.data) - 1):
            row = self.data.iloc[i]
            if np.isnan(row.get("senkou_a", np.nan)) or np.isnan(row.get("senkou_b", np.nan)):
                continue

            session_day = self.data.index[i].date() if hasattr(self.data.index[i], "date") else None
            if session_day is not None:
                day_count = trades_by_day.get(session_day, 0)
                if day_count >= max_daily_trades:
                    continue

            if i - last_signal_bar < cooldown_bars:
                continue

            final_direction = 0
            final_score = -1

            directions = ["long", "short"] if allow_short else ["long"]
            for direction in directions:
                l1 = layer1_check(row, direction)
                if not l1["pass"]:
                    continue

                l2 = layer2_check(self.data, i, direction)
                if not l2["pass"]:
                    continue

                l3 = layer3_check(row, direction)
                scored = score_signal(l1, l2, l3)
                if scored["total_score"] < min_score:
                    continue

                if scored["total_score"] > final_score:
                    final_score = scored["total_score"]
                    final_direction = 1 if direction == "long" else -1

            # Pyright struggles with get_loc union return type (int | slice | ndarray)
            col_idx = self.signals.columns.get_loc("signal")
            self.signals.iloc[i, col_idx] = final_direction  # pyright: ignore[reportArgumentType]
            if final_direction != 0:
                last_signal_bar = i
                if session_day is not None:
                    trades_by_day[session_day] = trades_by_day.get(session_day, 0) + 1

