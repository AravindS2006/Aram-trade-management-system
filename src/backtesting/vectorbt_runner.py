"""
VectorBT Backtesting Runner - Aram-TMS
Fast vectorized backtesting with accurate Indian market transaction costs.
"""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd
from loguru import logger
try:
    import vectorbt as vbt
    VBT_AVAILABLE = True
except ImportError:
    VBT_AVAILABLE = False
    logger.warning("vectorbt not installed: pip install vectorbt")
from src.strategies.base_strategy import BaseStrategy


@dataclass
class TransactionCostModel:
    """Accurate Indian market transaction cost model."""
    brokerage_per_order: float = 20.0      # Rs.20 flat (Dhan)
    slippage_pct: float = 0.0005           # 0.05%
    stt_pct: float = 0.001                 # 0.1% STT on sell (delivery)
    exchange_charges_pct: float = 0.0000345
    sebi_charges_pct: float = 0.000001
    gst_rate: float = 0.18
    stamp_duty_pct: float = 0.00015        # On buy
    dp_charges: float = 15.93             # Per scrip per sell (CDSL)
    segment: str = "equity_delivery"

    def round_trip_pct(self, trade_value: float = 100_000) -> float:
        brok = self.brokerage_per_order * 2
        stt = trade_value * self.stt_pct
        stamp = trade_value * self.stamp_duty_pct
        exch = trade_value * self.exchange_charges_pct * 2
        sebi = trade_value * self.sebi_charges_pct * 2
        gst = (brok + exch) * self.gst_rate
        slip = trade_value * self.slippage_pct * 2
        total = brok + stt + stamp + exch + sebi + gst + slip + self.dp_charges
        return total / trade_value


@dataclass
class BacktestResults:
    strategy_name: str
    strategy_params: Dict[str, Any]
    start_date: str
    end_date: str
    initial_capital: float
    final_value: float
    symbols: List[str]
    total_return: float = 0.0
    cagr: float = 0.0
    benchmark_return: float = 0.0
    alpha: float = 0.0
    beta: float = 0.0
    sharpe: float = 0.0
    sortino: float = 0.0
    calmar: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0
    volatility: float = 0.0
    num_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    expectancy: float = 0.0
    avg_holding_days: float = 0.0
    exposure_time: float = 0.0
    equity_curve: Optional[pd.Series] = None
    drawdown_series: Optional[pd.Series] = None
    trade_log: Optional[pd.DataFrame] = None
    engine: str = "vectorbt"
    run_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def print_summary(self) -> None:
        print(f"\n{'='*60}")
        print(f"  ARAM-TMS BACKTEST: {self.strategy_name}")
        print(f"{'='*60}")
        print(f"  Period: {self.start_date} -> {self.end_date}")
        print(f"  Capital: Rs.{self.initial_capital:,.0f} -> Rs.{self.final_value:,.0f}")
        print(f"  Total Return : {self.total_return:>9.2%}  CAGR: {self.cagr:.2%}  Alpha: {self.alpha:.2%}")
        print(f"  Sharpe       : {self.sharpe:>9.2f}  Sortino: {self.sortino:.2f}  Calmar: {self.calmar:.2f}")
        print(f"  Max Drawdown : {self.max_drawdown:>9.2%}  Volatility: {self.volatility:.2%}")
        print(f"  Trades       : {self.num_trades:>9}  Win Rate: {self.win_rate:.2%}  PF: {self.profit_factor:.2f}")
        print(f"  Expectancy   : Rs.{self.expectancy:>8,.0f}  Avg Hold: {self.avg_holding_days:.1f}d")
        print(f"{'='*60}\n")

    def save(self, output_dir: Union[str, Path] = "data/results/backtests") -> Path:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        p = output_dir / f"{self.strategy_name}_{ts}_summary.json"
        d = {k: v for k, v in self.__dict__.items() if not isinstance(v, (pd.Series, pd.DataFrame))}
        with open(p, "w") as f:
            json.dump(d, f, indent=2)
        if self.equity_curve is not None:
            self.equity_curve.to_frame("value").to_parquet(
                output_dir / f"{self.strategy_name}_{ts}_equity.parquet")
        if self.trade_log is not None:
            self.trade_log.to_parquet(output_dir / f"{self.strategy_name}_{ts}_trades.parquet")
        logger.info(f"Results saved: {p}")
        return p

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()
                if not isinstance(v, (pd.Series, pd.DataFrame))}


class VectorBTRunner:
    """
    High-speed vectorized backtesting via VectorBT.
    Best for: parameter optimization, large universes, rapid iteration.
    """
    def __init__(self, initial_capital: float = 1_000_000,
                 cost_model: Optional[TransactionCostModel] = None,
                 risk_free_rate: float = 0.065) -> None:
        if not VBT_AVAILABLE:
            raise ImportError("pip install vectorbt")
        self.initial_capital = initial_capital
        self.cost_model = cost_model or TransactionCostModel()
        self.risk_free_rate = risk_free_rate
        logger.info(f"VectorBTRunner | Capital: Rs.{initial_capital:,.0f} | "
                    f"Round-trip cost: {self.cost_model.round_trip_pct():.2%}")

    def run(self, strategy: BaseStrategy,
            data: Union[pd.DataFrame, Dict[str, pd.DataFrame]],
            benchmark_data: Optional[pd.DataFrame] = None) -> BacktestResults:
        strategy.validate_parameters()
        logger.info(f"Backtest: {strategy}")
        if isinstance(data, dict):
            return self._run_multi(strategy, data, benchmark_data)
        return self._run_single(strategy, data, benchmark_data)

    def _run_single(self, strategy, data, benchmark_data):
        close = data["Close"]
        raw = strategy.generate_signals(data)
        entries = (raw == 1) & (raw.shift(1) != 1)
        exits = ((raw == -1) | (raw == 0)) & (raw.shift(1) == 1)
        avg_pos_value = self.initial_capital * 0.05
        fees = self.cost_model.brokerage_per_order / max(avg_pos_value, 500) + self.cost_model.slippage_pct
        portfolio = vbt.Portfolio.from_signals(
            close=close, entries=entries, exits=exits,
            init_cash=self.initial_capital, fees=fees,
            slippage=self.cost_model.slippage_pct, freq="1D")
        return self._extract(portfolio, strategy, data, benchmark_data)

    def _run_multi(self, strategy, data_dict, benchmark_data):
        symbols = list(data_dict.keys())
        close = pd.DataFrame({s: d["Close"] for s, d in data_dict.items()}).dropna(how="all")
        sigs = pd.DataFrame({s: strategy.generate_signals(d)
                             for s, d in data_dict.items()}).reindex(close.index).fillna(0)
        entries = (sigs == 1) & (sigs.shift(1) != 1)
        exits = ((sigs == -1) | (sigs == 0)) & (sigs.shift(1) == 1)
        fees = self.cost_model.brokerage_per_order / (self.initial_capital / len(symbols) * 0.05) + self.cost_model.slippage_pct
        portfolio = vbt.Portfolio.from_signals(
            close=close, entries=entries, exits=exits,
            init_cash=self.initial_capital, fees=fees,
            slippage=self.cost_model.slippage_pct, freq="1D",
            size=1/len(symbols), size_type="Percent",
            group_by=True, cash_sharing=True)
        return self._extract(portfolio, strategy, close, benchmark_data, symbols=symbols)

    def _extract(self, portfolio, strategy, data, benchmark_data, symbols=None):
        equity = portfolio.value()
        trades = portfolio.trades.records_readable
        daily_rf = self.risk_free_rate / 252
        daily_ret = equity.pct_change().dropna()
        excess = daily_ret - daily_rf
        sharpe = float((excess.mean() / excess.std()) * np.sqrt(252)) if excess.std() > 0 else 0
        downside = excess[excess < 0]
        sortino = float((excess.mean() / downside.std()) * np.sqrt(252)) if len(downside) > 0 and downside.std() > 0 else 0
        total_return = float(equity.iloc[-1] / self.initial_capital - 1)
        years = max((equity.index[-1] - equity.index[0]).days / 365.25, 0.01)
        cagr = float((1 + total_return) ** (1/years) - 1)
        max_dd = float(portfolio.max_drawdown())
        calmar = cagr / abs(max_dd) if max_dd != 0 else 0
        bm_ret = alpha = beta = 0.0
        if benchmark_data is not None and not benchmark_data.empty:
            bm = benchmark_data["Close"].pct_change().dropna().reindex(daily_ret.index).fillna(0)
            bm_ret = float((1+bm).prod()-1)
            alpha = total_return - bm_ret
            if bm.var() > 0:
                beta = float(np.cov(daily_ret.fillna(0), bm)[0,1] / bm.var())
        n = len(trades)
        if n > 0:
            won = trades[trades["PnL"] > 0]; lost = trades[trades["PnL"] <= 0]
            win_rate = len(won)/n
            avg_win = float(won["PnL"].mean()) if len(won) else 0
            avg_loss = float(abs(lost["PnL"].mean())) if len(lost) else 0
            pf = float(won["PnL"].sum() / abs(lost["PnL"].sum())) if lost["PnL"].sum() < 0 else float("inf")
            exp = win_rate * avg_win - (1-win_rate) * avg_loss
        else:
            win_rate = avg_win = avg_loss = pf = exp = 0
        ref = data if isinstance(data, pd.DataFrame) else data
        r = BacktestResults(
            strategy_name=strategy.NAME, strategy_params=strategy.get_parameters(),
            start_date=str(equity.index[0].date()), end_date=str(equity.index[-1].date()),
            initial_capital=self.initial_capital, final_value=float(equity.iloc[-1]),
            symbols=symbols or ["primary"], total_return=total_return, cagr=cagr,
            benchmark_return=bm_ret, alpha=alpha, beta=beta, sharpe=sharpe,
            sortino=sortino, calmar=calmar, max_drawdown=max_dd,
            volatility=float(daily_ret.std()*np.sqrt(252)),
            num_trades=n, win_rate=win_rate, profit_factor=pf,
            avg_win=avg_win, avg_loss=avg_loss, expectancy=exp,
            equity_curve=equity, trade_log=trades, engine="vectorbt")
        r.print_summary()
        return r

    def optimize(self, strategy_class, data, param_grid, metric="sharpe", top_n=10):
        import itertools
        combos = [dict(zip(param_grid.keys(), c))
                  for c in itertools.product(*param_grid.values())]
        logger.info(f"Optimizing {strategy_class.NAME}: {len(combos)} combos")
        rows = []
        for p in combos:
            try:
                r = self.run(strategy_class(**p), data)
                row = p.copy(); row.update({"sharpe":r.sharpe,"cagr":r.cagr,
                    "max_drawdown":r.max_drawdown,"calmar":r.calmar,"win_rate":r.win_rate})
                rows.append(row)
            except Exception as e:
                logger.warning(f"{p} failed: {e}")
        df = pd.DataFrame(rows).sort_values(metric, ascending=False)
        logger.info(f"Best {metric}: {df[metric].iloc[0]:.2f}")
        return df.head(top_n)
