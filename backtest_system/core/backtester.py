import pandas as pd

from core.portfolio import Portfolio


class IntradayBacktester:
    """
    Event-driven simulation matching 1-minute sequential logic.
    Handles exact slippage, Stop Loss, Trailing Stop Loss, Take Profit, and 3:15 exits.
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
        self.portfolio = Portfolio(initial_capital=initial_capital)
        self.risk_per_trade_pct = risk_per_trade_pct
        self.fixed_quantity = quantity  # Simple position sizing for now
        self.commission = commission  # Flat commission per order (e.g. 20 INR)

        # Risk Management settings
        self.sl_pct = sl_pct
        self.tp_pct = tp_pct
        self.tsl_pct = tsl_pct
        self.slippage = slippage
        self.square_off_time = pd.to_datetime("15:15:00").time()

    def run(self) -> tuple[pd.DataFrame, dict]:
        position = 0  # 1 (Long), -1 (Short), 0 (Flat)
        current_qty = 0  # Track dynamic position quantity
        entry_price = 0.0
        current_sl = 0.0
        current_tp = 0.0
        max_favorable_price = 0.0
        symbol = "Symbol"  # Placeholder if single ticker backtest

        # Shift signal by 1 so execution happens on the bar AFTER the signal is generated. (Avoids lookahead bias)
        # Assuming signal 1=Buy, -1=Sell, 0=None
        self.data["exec_signal"] = self.data["signal"].shift(1).fillna(0)

        for row in self.data.itertuples():
            dt = row.Index
            if not isinstance(dt, pd.Timestamp):
                dt = pd.to_datetime(dt)

            current_time = dt.time()
            o, h, low, c = row.Open, row.High, row.Low, row.Close
            exec_signal = row.exec_signal

            # 1. Check for Forced Intraday Square-Off
            if position != 0 and current_time >= self.square_off_time:
                exit_price = c  # Market close
                # Apply slippage
                exit_price = (
                    exit_price * (1 - self.slippage)
                    if position == 1
                    else exit_price * (1 + self.slippage)
                )
                exit_price = round(exit_price, 3)

                self.portfolio.update_position(
                    symbol,
                    -position * current_qty,
                    exit_price,
                    dt,
                    transaction_cost=self.commission,
                    tag="TIME_EXIT",
                )
                position = 0
                current_qty = 0
                continue

            elif position != 0:
                exit_triggered = False

                # Check Stop Loss
                if position == 1 and low <= current_sl:
                    exit_price = round(
                        current_sl * (1 - self.slippage), 3
                    )  # Execution at SL level with slippage
                    exit_triggered = True
                    tag = "SL_HIT"
                elif position == -1 and h >= current_sl:
                    exit_price = round(current_sl * (1 + self.slippage), 3)
                    exit_triggered = True
                    tag = "SL_HIT"

                # Check Take Profit
                elif position == 1 and h >= current_tp:
                    exit_price = round(current_tp * (1 - self.slippage), 3)
                    exit_triggered = True
                    tag = "TP_HIT"
                elif position == -1 and low <= current_tp:
                    exit_price = round(current_tp * (1 + self.slippage), 3)
                    exit_triggered = True
                    tag = "TP_HIT"

                # Trailing Stop Logic (if price moves in favor)
                if not exit_triggered:
                    if position == 1:
                        if h > max_favorable_price:
                            max_favorable_price = h
                            new_sl = max_favorable_price * (1 - self.tsl_pct)
                            if new_sl > current_sl:
                                current_sl = new_sl
                    elif position == -1:
                        if low < max_favorable_price:
                            max_favorable_price = low
                            new_sl = max_favorable_price * (1 + self.tsl_pct)
                            if new_sl < current_sl:
                                current_sl = new_sl

                if exit_triggered:
                    self.portfolio.update_position(
                        symbol,
                        -position * current_qty,
                        exit_price,
                        dt,
                        transaction_cost=self.commission,
                        tag=tag,
                    )
                    position = 0
                    current_qty = 0
                    continue

            # 3. New Entry Logic (only if flat - simplifying)
            if position == 0 and current_time < self.square_off_time:
                if exec_signal == 1:  # Buy
                    entry_price = round(o * (1 + self.slippage), 3)

                    # Target Risk Sizing calculation
                    capital_at_risk = (
                        self.portfolio.total_value({symbol: c}) * self.risk_per_trade_pct
                    )
                    sl_amount = entry_price * self.sl_pct
                    current_qty = (
                        max(1, int(capital_at_risk / sl_amount))
                        if sl_amount > 0
                        else self.fixed_quantity
                    )

                    position = 1
                    self.portfolio.update_position(
                        symbol,
                        current_qty,
                        entry_price,
                        dt,
                        transaction_cost=self.commission,
                        tag="LONG_ENTRY",
                    )

                    # Set Risk Levels
                    current_sl = entry_price * (1 - self.sl_pct)
                    current_tp = entry_price * (1 + self.tp_pct)
                    max_favorable_price = entry_price

                elif exec_signal == -1:  # Sell
                    entry_price = round(o * (1 - self.slippage), 3)

                    # Target Risk Sizing calculation
                    capital_at_risk = (
                        self.portfolio.total_value({symbol: c}) * self.risk_per_trade_pct
                    )
                    sl_amount = entry_price * self.sl_pct
                    current_qty = (
                        max(1, int(capital_at_risk / sl_amount))
                        if sl_amount > 0
                        else self.fixed_quantity
                    )

                    position = -1
                    self.portfolio.update_position(
                        symbol,
                        -current_qty,
                        entry_price,
                        dt,
                        transaction_cost=self.commission,
                        tag="SHORT_ENTRY",
                    )

                    # Set Risk Levels
                    current_sl = entry_price * (1 + self.sl_pct)
                    current_tp = entry_price * (1 - self.tp_pct)
                    max_favorable_price = (
                        entry_price  # For short, lower is better, but we track low
                    )

        return self.portfolio.generate_tearsheet()
