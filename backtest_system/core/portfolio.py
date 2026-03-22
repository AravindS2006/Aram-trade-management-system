from datetime import datetime

import numpy as np
import pandas as pd

from core.costs import calculate_intraday_costs


class Portfolio:
    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: dict[str, int] = {}
        self.active_trades: dict[str, dict] = {}
        self.closed_trades: list[dict] = []
        self.equity_curve: list[dict] = []

    def total_value(self, current_prices: dict[str, float] | None = None) -> float:
        position_value = 0.0
        if current_prices:
            for symbol, qty in self.positions.items():
                if qty != 0:
                    price = current_prices.get(symbol, 0.0)
                    position_value += qty * price
        return self.cash + position_value

    def update_position(
        self,
        symbol: str,
        qty: int,
        price: float,
        timestamp: datetime,
        transaction_cost: float = 0.0,
        tag: str = "",
    ):
        price = round(price, 3)
        current_qty = self.positions.get(symbol, 0)
        new_qty = current_qty + qty

        if current_qty == 0 and qty != 0:
            self.active_trades[symbol] = {
                "entry_time": timestamp,
                "entry_price": price,
                "quantity": qty,
                "tag": tag,
            }
        elif new_qty == 0:
            if symbol in self.active_trades:
                entry = self.active_trades.pop(symbol)

                if entry["quantity"] > 0:
                    buy_price = entry["entry_price"]
                    sell_price = price
                else:
                    buy_price = price
                    sell_price = entry["entry_price"]

                abs_qty = abs(entry["quantity"])

                cost_data = calculate_intraday_costs(buy_price, sell_price, abs_qty)

                if entry["quantity"] > 0:
                    gross_pnl = (sell_price - buy_price) * abs_qty
                else:
                    gross_pnl = (entry["entry_price"] - price) * abs_qty

                net_pnl = round(gross_pnl - cost_data["total_charges"], 3)
                self.cash += net_pnl

                self.closed_trades.append(
                    {
                        "Symbol": symbol,
                        "Entry Time": entry["entry_time"],
                        "Exit Time": timestamp,
                        "Entry Price": round(entry["entry_price"], 2),
                        "Exit Price": round(price, 2),
                        "Quantity": entry["quantity"],
                        "Gross PnL": round(gross_pnl, 2),
                        "Taxes & Charges": round(cost_data["total_charges"], 2),
                        "Net PnL": round(net_pnl, 2),
                        "Tag": tag,
                    }
                )

        self.positions[symbol] = new_qty
        current_val = self.initial_capital + sum([t["Net PnL"] for t in self.closed_trades])
        self.equity_curve.append({"timestamp": timestamp, "equity": current_val})

    def generate_tearsheet(self):
        trades_df = pd.DataFrame(self.closed_trades)
        if trades_df.empty:
            return None, {}

        trades_df["Cumulative Net PnL"] = trades_df["Net PnL"].cumsum()
        trades_df["Equity"] = self.initial_capital + trades_df["Cumulative Net PnL"]

        total_trades = len(trades_df)
        winning_df = trades_df[trades_df["Net PnL"] > 0]
        losing_df = trades_df[trades_df["Net PnL"] < 0]

        win_rate = len(winning_df) / total_trades if total_trades > 0 else 0
        gross_profit = winning_df["Net PnL"].sum()
        gross_loss = abs(losing_df["Net PnL"].sum())
        profit_factor = gross_profit / gross_loss if gross_loss != 0 else 0.0

        trades_df["Peak"] = trades_df["Equity"].cummax()
        trades_df["Drawdown"] = (trades_df["Equity"] - trades_df["Peak"]) / trades_df["Peak"]
        max_dd = trades_df["Drawdown"].min()

        trades_df["Trough"] = trades_df["Equity"].cummin()
        trades_df["Runup"] = (trades_df["Equity"] - trades_df["Trough"]) / trades_df["Trough"]
        max_runup = trades_df["Runup"].max()

        total_pnl = trades_df["Net PnL"].sum()
        total_charges = (
            trades_df["Taxes & Charges"].sum() if "Taxes & Charges" in trades_df.columns else 0.0
        )
        return_pct = (total_pnl / self.initial_capital) * 100
        final_equity = self.initial_capital + total_pnl

        avg_win = winning_df["Net PnL"].mean() if not winning_df.empty else 0.0
        avg_loss = losing_df["Net PnL"].mean() if not losing_df.empty else 0.0

        win_loss_ratio = avg_win / abs(avg_loss) if avg_loss != 0 else 0
        kelly_pct = win_rate - ((1 - win_rate) / win_loss_ratio) if win_loss_ratio > 0 else 0

        metrics = {
            "Initial Capital": f"₹ {self.initial_capital:,.2f}",
            "Final Equity": f"₹ {final_equity:,.2f}",
            "Total Return %": f"{return_pct:.2f}%",
            "Max Drawdown %": f"{max_dd * 100:.2f}%",
            "Max Run-up %": f"{max_runup * 100:.2f}%",
            "Total Trades": total_trades,
            "Win Rate %": f"{win_rate * 100:.2f}%",
            "Profit Factor": round(profit_factor, 3),
            "Kelly Criterion": f"{kelly_pct * 100:.2f}%",
            "Avg Winning Trade": f"₹ {avg_win:,.2f}",
            "Avg Losing Trade": f"₹ {avg_loss:,.2f}",
            "Total Charges Paid": f"₹ {total_charges:,.2f}",
            "Sharpe Ratio": round(self._calculate_sharpe(trades_df), 3),
        }

        return trades_df, metrics

    def _calculate_sharpe(self, trades_df):
        if len(trades_df) < 2:
            return 0.0
        trades_df["Return %"] = trades_df["Net PnL"] / (
            trades_df["Entry Price"] * trades_df["Quantity"].abs()
        )
        mean_ret = trades_df["Return %"].mean()
        std_ret = trades_df["Return %"].std()
        if std_ret == 0:
            return 0.0
        return (mean_ret / std_ret) * np.sqrt(252)
