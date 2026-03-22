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
        self.data["sl_price"] = pd.NA
        self.data["tp_price"] = pd.NA

        in_trade = 0
        for idx, row in self.data.iterrows():
            if any(pd.isna(row[k]) for k in self.cfg.SCORE_REQUIRED_COLUMNS):
                continue

            long_score = score_signal(row, "long", self.cfg)
            short_score = score_signal(row, "short", self.cfg)
            self.data.at[idx, "score_long"] = long_score
            self.data.at[idx, "score_short"] = short_score

            is_long = long_score >= self.cfg.HALF_SCORE and long_score >= short_score
            is_short = short_score >= self.cfg.HALF_SCORE and short_score > long_score

            if is_long:
                if in_trade != 1:
                    self.signals.at[idx, "signal"] = 1
                    in_trade = 1
                    
                    # Calculate dynamic SL/TP based on ATR rules
                    entry = row["close"]
                    atr = row["atr"]
                    sl_dist = max(self.cfg.ATR_SL_MULT * atr, entry * 0.002)
                    self.data.at[idx, "sl_price"] = entry - sl_dist
                    self.data.at[idx, "tp_price"] = entry + (sl_dist * self.cfg.RR1)
            elif is_short:
                if in_trade != -1:
                    self.signals.at[idx, "signal"] = -1
                    in_trade = -1
                    
                    entry = row["close"]
                    atr = row["atr"]
                    sl_dist = max(self.cfg.ATR_SL_MULT * atr, entry * 0.002)
                    self.data.at[idx, "sl_price"] = entry + sl_dist
                    self.data.at[idx, "tp_price"] = entry - (sl_dist * self.cfg.RR1)
            else:
                in_trade = 0

        self.signals["signal"] = self.signals["signal"].astype(int)
