"""BaseStrategy adapter for the Weapon Candle confluence system."""

from __future__ import annotations

import pandas as pd

from core.strategy import BaseStrategy
from strategies.weapon_candle.config import CFG, WeaponCandleConfig
from strategies.weapon_candle.data.preprocessor import preprocess
from strategies.weapon_candle.indicators.pipeline import apply_all_indicators
from strategies.weapon_candle.signals.scorer import score_signal


class WeaponCandleSystemStrategy(BaseStrategy):
    """Generate -1/0/1 signals using the document-defined 4-layer scorer."""

    def __init__(self, data: pd.DataFrame, params: dict | None = None):
        super().__init__(data, params)
        self.cfg: WeaponCandleConfig = CFG

    def _normalize_input(self) -> pd.DataFrame:
        """Map OHLCV columns to lowercase names expected by strategy modules."""
        rename_map = {
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        }
        out = self.data.rename(columns=rename_map).copy()
        required = ["open", "high", "low", "close", "volume"]
        missing = [c for c in required if c not in out.columns]
        if missing:
            raise ValueError(f"Missing required columns for Weapon Candle: {missing}")
        return out

    def generate_indicators(self):
        """Compute all indicator columns in canonical order."""
        base = self._normalize_input()
        base = preprocess(base, self.cfg)
        enriched = apply_all_indicators(base, self.cfg)
        self.data = enriched

    def generate_signals(self):
        """Emit integer signals and optional stop/target hints."""
        self.signals["signal"] = 0
        self.data["score_long"] = -1
        self.data["score_short"] = -1
        from strategies.weapon_candle.utils.time_filter import in_entry_session

        in_trade = 0
        daily_trades = 0
        current_date = None

        for idx, row in self.data.iterrows():
            ts_date = idx.date()
            if current_date != ts_date:
                current_date = ts_date
                daily_trades = 0
                in_trade = 0

            ts_time = idx.time()
            if not in_entry_session(ts_time, self.cfg):
                in_trade = 0
                continue

            if daily_trades >= self.cfg.MAX_DAILY_TRADES:
                continue

            if any(pd.isna(row[k]) for k in self.cfg.SCORE_REQUIRED_COLUMNS):
                continue

            long_score = score_signal(row, "long", self.cfg)
            short_score = score_signal(row, "short", self.cfg)
            self.data.at[idx, "score_long"] = long_score
            self.data.at[idx, "score_short"] = short_score
            
            # Size multiplier based on score
            score_to_use = max(long_score, short_score)
            size_mult = 1.0 if score_to_use >= self.cfg.MIN_SCORE else (0.5 if score_to_use >= self.cfg.HALF_SCORE else 0.0)
            self.data.at[idx, "size_mult"] = size_mult

            is_long = long_score >= self.cfg.MIN_SCORE and long_score >= short_score
            is_short = short_score >= self.cfg.MIN_SCORE and short_score > long_score

            if is_long:
                if in_trade != 1:
                    self.signals.at[idx, "signal"] = 1
                    in_trade = 1
                    daily_trades += 1
                    
                    # Calculate dynamic SL/TP based on ATR rules, but respect UI overrides
                    entry = row["close"]
                    atr = row["atr"]
                    
                    # If SL% is provided in UI, use it. Otherwise use ATR-based.
                    ui_sl_pct = self.params.get("sl_pct", 0)
                    if ui_sl_pct > 0:
                        sl_dist = entry * ui_sl_pct
                    else:
                        sl_dist = max(self.cfg.ATR_SL_MULT * atr, entry * 0.002)
                        
                    self.data.at[idx, "sl_price"] = entry - sl_dist
                    
                    # Target 1: Respect UI TP% if provided, otherwise 1.8R
                    ui_tp_pct = self.params.get("tp_pct", 0)
                    if ui_tp_pct > 0:
                        self.data.at[idx, "target1_price"] = entry + (entry * ui_tp_pct * 0.5) # Scale out at half of TP
                        self.data.at[idx, "target2_price"] = entry + (entry * ui_tp_pct)
                    else:
                        self.data.at[idx, "target1_price"] = entry + (sl_dist * self.cfg.RR1)
                        self.data.at[idx, "target2_price"] = entry + (sl_dist * self.cfg.RR2)
                    
                    self.data.at[idx, "tp_price"] = self.data.at[idx, "target1_price"]
            elif is_short:
                if in_trade != -1:
                    self.signals.at[idx, "signal"] = -1
                    in_trade = -1
                    daily_trades += 1
                    
                    entry = row["close"]
                    atr = row["atr"]
                    
                    ui_sl_pct = self.params.get("sl_pct", 0)
                    if ui_sl_pct > 0:
                        sl_dist = entry * ui_sl_pct
                    else:
                        sl_dist = max(self.cfg.ATR_SL_MULT * atr, entry * 0.002)
                        
                    self.data.at[idx, "sl_price"] = entry + sl_dist
                    
                    ui_tp_pct = self.params.get("tp_pct", 0)
                    if ui_tp_pct > 0:
                        self.data.at[idx, "target1_price"] = entry - (entry * ui_tp_pct * 0.5)
                        self.data.at[idx, "target2_price"] = entry - (entry * ui_tp_pct)
                    else:
                        self.data.at[idx, "target1_price"] = entry - (sl_dist * self.cfg.RR1)
                        self.data.at[idx, "target2_price"] = entry - (sl_dist * self.cfg.RR2)
                    
                    self.data.at[idx, "tp_price"] = self.data.at[idx, "target1_price"]
            else:
                in_trade = 0

        # Populate trail_price column for the whole dataframe for backtester to use
        self.data["trail_price"] = self.data["ema9"]
        self.signals["signal"] = self.signals["signal"].astype(int)
