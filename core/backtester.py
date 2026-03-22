import pandas as pd
import numpy as np
from core.portfolio import Portfolio

class IntradayBacktester:
    """
    Event-driven simulation matching 1-minute sequential logic.
    Handles exact slippage, Stop Loss, Trailing Stop Loss, Take Profit, and 3:15 exits.
    Supports partial exits (Target 1) and dynamic indicator-based trailing.
    """

    def __init__(
        self,
        data_with_signals: pd.DataFrame,
        initial_capital: float = 100000,
        risk_per_trade_pct: float = 0.01,
        sl_pct: float = 0.01,
        tp_pct: float = 0.02,
        tsl_pct: float = 0.005,
        slippage: float = 0.0005,
        quantity: int = 1,
        commission: float = 20.0,
    ):
        self.data = data_with_signals.copy()
        # Keep backtester compatible with both legacy (Open/High/Low/Close)
        # and normalized (open/high/low/close) strategy outputs.
        alias_map = {
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
        }
        for src, dst in alias_map.items():
            if src in self.data.columns and dst not in self.data.columns:
                self.data[dst] = self.data[src]

        self.portfolio = Portfolio(initial_capital=initial_capital)
        self.risk_per_trade_pct = risk_per_trade_pct
        self.fixed_quantity = quantity
        self.commission = commission

        # Risk Management settings
        self.sl_pct = sl_pct
        self.tp_pct = tp_pct
        self.tsl_pct = tsl_pct
        self.slippage = slippage
        self.square_off_time = pd.to_datetime("15:15:00").time()

    def run(self) -> tuple[pd.DataFrame, dict]:
        position = 0  # 1 (Long), -1 (Short), 0 (Flat)
        current_qty = 0
        entry_price = 0.0
        current_sl = 0.0
        current_sl_pct = self.sl_pct
        current_tp = 0.0
        current_t1 = 0.0
        current_t2 = 0.0
        target1_hit = False
        max_favorable_price = 0.0
        tsl_active = False 
        symbol = "Symbol"

        # Shift signals and risk prices to avoid lookahead bias
        self.data["exec_signal"] = self.data["signal"].shift(1).fillna(0)
        
        risk_cols = ["sl_price", "tp_price", "target1_price", "target2_price", "trail_price", "size_mult"]
        for col in risk_cols:
            if col in self.data.columns:
                self.data[f"exec_{col}"] = self.data[col].shift(1)

        for row in self.data.itertuples():
            dt = row.Index
            if not isinstance(dt, pd.Timestamp):
                dt = pd.to_datetime(dt)

            current_time = dt.time()
            o, h, low, c = row.Open, row.High, row.Low, row.Close
            exec_signal = row.exec_signal

            # Read dynamic risk levels
            dyn_sl = float(row.exec_sl_price) if hasattr(row, "exec_sl_price") and pd.notna(row.exec_sl_price) else None
            dyn_tp = float(row.exec_tp_price) if hasattr(row, "exec_tp_price") and pd.notna(row.exec_tp_price) else None
            dyn_t1 = float(row.exec_target1_price) if hasattr(row, "exec_target1_price") and pd.notna(row.exec_target1_price) else None
            dyn_t2 = float(row.exec_target2_price) if hasattr(row, "exec_target2_price") and pd.notna(row.exec_target2_price) else None
            dyn_trail = float(row.exec_trail_price) if hasattr(row, "exec_trail_price") and pd.notna(row.exec_trail_price) else None
            dyn_size_mult = float(row.exec_size_mult) if hasattr(row, "exec_size_mult") and pd.notna(row.exec_size_mult) else 1.0

            # 1. Check for Forced Intraday Square-Off
            if position != 0 and current_time >= self.square_off_time:
                exit_price = round(c * (1 - self.slippage) if position == 1 else c * (1 + self.slippage), 3)
                self.portfolio.update_position(symbol, -position * current_qty, exit_price, dt, transaction_cost=self.commission, tag="TIME_EXIT")
                position, current_qty = 0, 0
                continue

            elif position != 0:
                exit_triggered = False

                # Check Stop Loss
                if (position == 1 and low <= current_sl) or (position == -1 and h >= current_sl):
                    exit_price = round(current_sl * (1 - self.slippage) if position == 1 else current_sl * (1 + self.slippage), 3)
                    exit_triggered, tag = True, "SL_HIT"

                # Check Targets
                if not exit_triggered:
                    # Target 1 (Partial Exit 50%)
                    if not target1_hit and current_t1 > 0:
                        if (position == 1 and h >= current_t1) or (position == -1 and low <= current_t1):
                            exit_price = round(current_t1 * (1 - self.slippage) if position == 1 else current_t1 * (1 + self.slippage), 3)
                            partial_qty = current_qty // 2
                            if partial_qty > 0:
                                self.portfolio.update_position(symbol, -position * partial_qty, exit_price, dt, transaction_cost=self.commission, tag="PARTIAL_T1")
                                current_qty -= partial_qty
                                target1_hit = True
                                current_sl = entry_price  # Move Stop to Breakeven
                                current_sl_pct = 0.0

                    # Target 2 or TP
                    final_tp = current_t2 if current_t2 > 0 else current_tp
                    if final_tp > 0:
                        if (position == 1 and h >= final_tp) or (position == -1 and low <= final_tp):
                            exit_price = round(final_tp * (1 - self.slippage) if position == 1 else final_tp * (1 + self.slippage), 3)
                            exit_triggered, tag = True, "TP_HIT"

                # Trailing logic
                if not exit_triggered:
                    if target1_hit and dyn_trail is not None:
                        if (position == 1 and dyn_trail > current_sl) or (position == -1 and dyn_trail < current_sl):
                            current_sl = dyn_trail
                    
                    if self.tsl_pct > 0:
                        if position == 1:
                            if h > max_favorable_price: max_favorable_price = h
                            if not tsl_active:
                                if max_favorable_price >= entry_price * (1 + current_sl_pct):
                                    tsl_active = True
                                    current_sl = max_favorable_price * (1 - self.tsl_pct)
                            else:
                                new_sl = max_favorable_price * (1 - self.tsl_pct)
                                if new_sl > current_sl: current_sl = new_sl
                        elif position == -1:
                            if low < max_favorable_price: max_favorable_price = low
                            if not tsl_active:
                                if max_favorable_price <= entry_price * (1 - current_sl_pct):
                                    tsl_active = True
                                    current_sl = max_favorable_price * (1 + self.tsl_pct)
                            else:
                                new_sl = max_favorable_price * (1 + self.tsl_pct)
                                if new_sl < current_sl: current_sl = new_sl

                if exit_triggered:
                    self.portfolio.update_position(symbol, -position * current_qty, exit_price, dt, transaction_cost=self.commission, tag=tag)
                    position, current_qty = 0, 0
                    continue

            # 3. New Entry Logic
            if position == 0 and current_time < self.square_off_time:
                if exec_signal != 0:
                    position = int(exec_signal)
                    side = "LONG" if position == 1 else "SHORT"
                    entry_price = round(o * (1 + self.slippage if position == 1 else 1 - self.slippage), 3)

                    # Risk Levels
                    current_sl = dyn_sl if dyn_sl is not None else entry_price * (1 - self.sl_pct if position == 1 else 1 + self.sl_pct)
                    current_sl_pct = abs(entry_price - current_sl) / entry_price if entry_price > 0 else self.sl_pct
                    current_tp = dyn_tp if dyn_tp is not None else entry_price * (1 + self.tp_pct if position == 1 else 1 - self.tp_pct)
                    current_t1 = dyn_t1 if dyn_t1 is not None else 0.0
                    current_t2 = dyn_t2 if dyn_t2 is not None else 0.0
                    target1_hit = False

                    # Sizing
                    capital_at_risk = self.portfolio.total_value({symbol: c}) * self.risk_per_trade_pct * dyn_size_mult
                    sl_amount = entry_price * current_sl_pct
                    current_qty = max(1, int(capital_at_risk / sl_amount)) if sl_amount > 0 else self.fixed_quantity

                    self.portfolio.update_position(symbol, position * current_qty, entry_price, dt, transaction_cost=self.commission, tag=f"{side}_ENTRY")
                    max_favorable_price, tsl_active = entry_price, False

                    # Intra-bar exit check
                    if (position == 1 and low <= current_sl) or (position == -1 and h >= current_sl):
                        exit_price = round(current_sl * (1 - self.slippage if position == 1 else 1 + self.slippage), 3)
                        self.portfolio.update_position(symbol, -position * current_qty, exit_price, dt, transaction_cost=self.commission, tag="SL_HIT")
                        position, current_qty = 0, 0
                    elif (position == 1 and h >= current_tp) or (position == -1 and low <= current_tp):
                        exit_price = round(current_tp * (1 - self.slippage if position == 1 else 1 + self.slippage), 3)
                        self.portfolio.update_position(symbol, -position * current_qty, exit_price, dt, transaction_cost=self.commission, tag="TP_HIT")
                        position, current_qty = 0, 0

        return self.portfolio.generate_tearsheet()
