"""
Backtrader Event-Driven Runner - Aram-TMS
Realistic order simulation with proper fills, slippage, and broker commission.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd
from loguru import logger
try:
    import backtrader as bt
    import backtrader.analyzers as bta
    BT_AVAILABLE = True
except ImportError:
    BT_AVAILABLE = False
    logger.warning("backtrader not installed: pip install backtrader")
from src.strategies.base_strategy import BaseStrategy
from src.backtesting.vectorbt_runner import BacktestResults, TransactionCostModel


class BTStrategyWrapper(bt.Strategy):
    """Wraps Aram-TMS strategy into Backtrader."""
    params = dict(aram_strategy=None, print_log=False)

    def __init__(self):
        self.aram = self.params.aram_strategy
        self.orders = {}
        self.trade_log = []
        self._precomputed: Dict[str, pd.Series] = {}

    def next(self):
        for data in self.datas:
            sym = data._name
            if self.orders.get(sym): continue
            bar_idx = len(data) - 1
            sig = int(self._precomputed.get(sym, pd.Series()).iloc[bar_idx]
                      if sym in self._precomputed and bar_idx < len(self._precomputed[sym]) else 0)
            pos = self.getposition(data).size
            if sig == 1 and pos <= 0:
                price = data.close[0]
                pv = self.broker.getvalue()
                atr = max(data.high[0] - data.low[0], abs(data.high[0]-data.close[-1]),
                          abs(data.low[0]-data.close[-1])) if len(data) > 1 else price*0.02
                sl = self.aram.get_stop_loss(price, 1, atr)
                qty = self.aram.get_position_size(pv, price, sl)
                if qty > 0 and price * qty <= pv * 0.95:
                    self.orders[sym] = self.buy(data=data, size=qty, exectype=bt.Order.Market)
            elif sig <= 0 and pos > 0:
                self.orders[sym] = self.close(data=data)

    def notify_order(self, order):
        sym = order.data._name
        if order.status in [order.Completed] and sym in self.orders:
            self.orders[sym] = None
        elif order.status in [order.Canceled, order.Rejected] and sym in self.orders:
            self.orders[sym] = None

    def notify_trade(self, trade):
        if trade.isclosed:
            self.trade_log.append({"symbol": trade.data._name, "pnl": trade.pnl,
                                   "pnl_net": trade.pnlcomm, "bars": trade.barlen})


class BacktraderRunner:
    """Event-driven backtesting with realistic order fills."""
    def __init__(self, initial_capital: float = 1_000_000,
                 cost_model: Optional[TransactionCostModel] = None,
                 risk_free_rate: float = 0.065, slippage_pct: float = 0.0005) -> None:
        if not BT_AVAILABLE:
            raise ImportError("pip install backtrader")
        self.initial_capital = initial_capital
        self.cost_model = cost_model or TransactionCostModel()
        self.risk_free_rate = risk_free_rate
        self.slippage_pct = slippage_pct

    def run(self, strategy: BaseStrategy, data: Union[pd.DataFrame, Dict[str, pd.DataFrame]],
            benchmark_data: Optional[pd.DataFrame] = None, plot: bool = False) -> BacktestResults:
        strategy.validate_parameters()
        logger.info(f"Backtrader: {strategy}")
        # Pre-compute signals
        if isinstance(data, dict):
            sig_map = {s: strategy.generate_signals(d) for s, d in data.items()}
        else:
            sig_map = {"primary": strategy.generate_signals(data)}
        cerebro = bt.Cerebro()
        cerebro.broker.setcash(self.initial_capital)
        cerebro.broker.setcommission(commission=20, commtype=bt.CommInfoBase.COMM_FIXED)
        cerebro.broker.set_slippage_perc(self.slippage_pct)
        if isinstance(data, dict):
            for sym, df in data.items():
                cerebro.adddata(self._feed(df), name=sym)
        else:
            cerebro.adddata(self._feed(data), name="primary")
        cerebro.addstrategy(BTStrategyWrapper, aram_strategy=strategy)
        for name, cls, kwargs in [
            ("sharpe", bta.SharpeRatio, {"riskfreerate":self.risk_free_rate,"annualize":True,"timeframe":bt.TimeFrame.Days}),
            ("drawdown", bta.DrawDown, {}),
            ("trades", bta.TradeAnalyzer, {}),
            ("timereturn", bta.TimeReturn, {})]:
            cerebro.addanalyzer(cls, _name=name, **kwargs)
        start_val = cerebro.broker.getvalue()
        results_list = cerebro.run()
        end_val = cerebro.broker.getvalue()
        if plot:
            try: cerebro.plot(style="candlestick", iplot=False)
            except Exception: pass
        return self._extract(results_list[0], strategy, start_val, end_val,
                             data, benchmark_data, sig_map)

    def _feed(self, df):
        df = df.rename(columns={c: c.title() for c in df.columns})
        return bt.feeds.PandasData(dataname=df, datetime=None,
                                   open="Open", high="High", low="Low",
                                   close="Close", volume="Volume", openinterest=-1)

    def _extract(self, strat, strategy, start_val, end_val, data, benchmark_data, sig_map):
        ref = data if isinstance(data, pd.DataFrame) else list(data.values())[0]
        total_return = (end_val / start_val) - 1
        years = max((ref.index[-1]-ref.index[0]).days / 365.25, 0.01)
        cagr = (1+total_return)**(1/years)-1
        try:
            dd_a = strat.analyzers.drawdown.get_analysis()
            max_dd = float(dd_a.get("max",{}).get("drawdown",0) or 0)/100
            dd_dur = int(dd_a.get("max",{}).get("len",0) or 0)
        except Exception: max_dd=dd_dur=0
        try:
            sha = strat.analyzers.sharpe.get_analysis()
            sharpe = float(sha.get("sharperatio",0) or 0)
        except Exception: sharpe=0.0
        try:
            ta = strat.analyzers.trades.get_analysis()
            n = int(ta.get("total",{}).get("closed",0) or 0)
            w = ta.get("won",{}); l = ta.get("lost",{})
            win_rate = int(w.get("total",0) or 0)/n if n else 0
            avg_win = float(w.get("pnl",{}).get("average",0) or 0)
            avg_loss = abs(float(l.get("pnl",{}).get("average",0) or 0))
            tw = float(w.get("pnl",{}).get("total",0) or 0)
            tl = abs(float(l.get("pnl",{}).get("total",0) or 0))
            pf = tw/tl if tl > 0 else float("inf")
        except Exception: n=win_rate=avg_win=avg_loss=pf=0
        try:
            tr_returns = pd.Series(strat.analyzers.timereturn.get_analysis())
            vol = float(tr_returns.std()*np.sqrt(252))
            downside = tr_returns[tr_returns < 0]
            sortino = float((tr_returns.mean()/downside.std())*np.sqrt(252)) if len(downside) > 0 and downside.std() > 0 else 0
        except Exception: vol=sortino=0.0
        calmar = cagr/abs(max_dd) if max_dd > 0 else 0
        bm_ret=alpha=0.0
        if benchmark_data is not None and not benchmark_data.empty:
            bm = benchmark_data["Close"].pct_change().dropna()
            bm_ret = float((1+bm).prod()-1)
            alpha = total_return - bm_ret
        trade_log = pd.DataFrame(strat.trade_log) if strat.trade_log else pd.DataFrame()
        r = BacktestResults(
            strategy_name=strategy.NAME, strategy_params=strategy.get_parameters(),
            start_date=str(ref.index[0].date()), end_date=str(ref.index[-1].date()),
            initial_capital=start_val, final_value=end_val,
            symbols=list(data.keys()) if isinstance(data, dict) else ["primary"],
            total_return=total_return, cagr=cagr, benchmark_return=bm_ret, alpha=alpha,
            sharpe=sharpe, sortino=sortino, calmar=calmar, max_drawdown=max_dd,
            max_drawdown_duration=dd_dur, volatility=vol, num_trades=n, win_rate=win_rate,
            profit_factor=pf, avg_win=avg_win, avg_loss=avg_loss,
            expectancy=win_rate*avg_win - (1-win_rate)*avg_loss,
            trade_log=trade_log if not trade_log.empty else None, engine="backtrader")
        r.print_summary()
        return r
