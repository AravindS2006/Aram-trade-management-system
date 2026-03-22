"""
Walk-Forward Optimizer - Aram-TMS
Prevents overfitting via rolling/anchored out-of-sample validation.
"""
from __future__ import annotations
import itertools
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Type
import numpy as np
import pandas as pd
from loguru import logger
from src.strategies.base_strategy import BaseStrategy
from src.backtesting.vectorbt_runner import VectorBTRunner, BacktestResults, TransactionCostModel


@dataclass
class WFOWindow:
    window_id: int
    train_start: str; train_end: str
    test_start: str; test_end: str
    best_params: Dict[str, Any] = field(default_factory=dict)
    train_metric: float = 0.0
    test_metric: float = 0.0


@dataclass
class WFOResults:
    strategy_name: str
    windows: List[WFOWindow]
    combined_equity: pd.Series
    oos_sharpe: float
    oos_return: float
    oos_max_dd: float
    efficiency_ratio: float        # OOS/IS metric ratio (robustness check)
    best_params_frequency: Dict[str, Any]
    param_stability: float

    def print_summary(self) -> None:
        print(f"\n{'='*60}")
        print(f"  WALK-FORWARD RESULTS: {self.strategy_name}")
        print(f"{'='*60}")
        print(f"  Windows     : {len(self.windows)}")
        print(f"  OOS Sharpe  : {self.oos_sharpe:.2f}")
        print(f"  OOS Return  : {self.oos_return:.2%}")
        print(f"  OOS Max DD  : {self.oos_max_dd:.2%}")
        print(f"  Efficiency  : {self.efficiency_ratio:.2f}  (IS->OOS robustness; >0.7 good)")
        print(f"  Param Stab  : {self.param_stability:.2%}")
        print(f"\n  Per-Window:")
        for w in self.windows:
            print(f"    W{w.window_id}: Train {w.train_start}->{w.train_end} "
                  f"IS={w.train_metric:.2f} | Test {w.test_start}->{w.test_end} "
                  f"OOS={w.test_metric:.2f} | {w.best_params}")
        print(f"{'='*60}\n")


class WalkForwardOptimizer:
    """
    Walk-Forward Optimization (WFO).
    Methods: rolling (fixed train+test windows) or anchored (growing train window).
    """
    def __init__(self, strategy_class: Type[BaseStrategy], param_grid: Dict[str, List[Any]],
                 train_window: int = 252, test_window: int = 63, step_size: int = 63,
                 method: str = "rolling", metric: str = "sharpe",
                 initial_capital: float = 1_000_000,
                 cost_model: Optional[TransactionCostModel] = None) -> None:
        self.strategy_class = strategy_class
        self.param_grid = param_grid
        self.train_window = train_window
        self.test_window = test_window
        self.step_size = step_size
        self.method = method
        self.metric = metric
        self.initial_capital = initial_capital
        self.cost_model = cost_model or TransactionCostModel()
        self.combinations = [dict(zip(param_grid.keys(), c))
                             for c in itertools.product(*param_grid.values())]
        logger.info(f"WFO: {strategy_class.NAME} | {len(self.combinations)} combos | "
                    f"{method} | train={train_window}d test={test_window}d")

    def run(self, data: pd.DataFrame,
            benchmark_data: Optional[pd.DataFrame] = None) -> WFOResults:
        windows_spec = self._build_windows(data)
        logger.info(f"Running {len(windows_spec)} WFO windows")
        wfo_windows, equity_parts = [], []
        for i, (train_sl, test_sl) in enumerate(windows_spec):
            logger.info(f"Window {i+1}/{len(windows_spec)}: "
                        f"train {train_sl.index[0].date()}->{train_sl.index[-1].date()} | "
                        f"test {test_sl.index[0].date()}->{test_sl.index[-1].date()}")
            best_params, is_metric, _ = self._optimize(train_sl, benchmark_data)
            oos_result = self._test(best_params, test_sl, benchmark_data)
            oos_metric = getattr(oos_result, self.metric, 0)
            wfo_windows.append(WFOWindow(
                window_id=i+1,
                train_start=str(train_sl.index[0].date()),
                train_end=str(train_sl.index[-1].date()),
                test_start=str(test_sl.index[0].date()),
                test_end=str(test_sl.index[-1].date()),
                best_params=best_params, train_metric=is_metric, test_metric=oos_metric))
            if oos_result.equity_curve is not None:
                equity_parts.append(oos_result.equity_curve)
        combined = self._chain_equity(equity_parts)
        oos_sharpe = self._sharpe(combined)
        oos_ret = float(combined.iloc[-1]/combined.iloc[0]-1) if len(combined) > 1 else 0
        oos_dd = float((combined/combined.cummax()-1).min()) if len(combined) > 1 else 0
        all_params = [w.best_params for w in wfo_windows]
        avg_is = np.mean([w.train_metric for w in wfo_windows])
        avg_oos = np.mean([w.test_metric for w in wfo_windows])
        efficiency = avg_oos / avg_is if avg_is > 0 else 0
        stability = self._param_stability(all_params)
        most_common = self._most_common_params(all_params)
        results = WFOResults(
            strategy_name=self.strategy_class.NAME, windows=wfo_windows,
            combined_equity=combined, oos_sharpe=oos_sharpe, oos_return=oos_ret,
            oos_max_dd=oos_dd, efficiency_ratio=efficiency,
            best_params_frequency=most_common, param_stability=stability)
        results.print_summary()
        return results

    def _build_windows(self, data):
        windows, n = [], len(data)
        if self.method == "rolling":
            start = 0
            while start + self.train_window + self.test_window <= n:
                te = start + self.train_window
                windows.append((data.iloc[start:te], data.iloc[te:te+self.test_window]))
                start += self.step_size
        else:  # anchored
            te = self.train_window
            while te + self.test_window <= n:
                windows.append((data.iloc[0:te], data.iloc[te:te+self.test_window]))
                te += self.step_size
        return windows

    def _optimize(self, train_data, benchmark_data):
        runner = VectorBTRunner(initial_capital=self.initial_capital, cost_model=self.cost_model)
        results = []
        for params in self.combinations:
            try:
                r = runner.run(self.strategy_class(**params), train_data, benchmark_data)
                m = getattr(r, self.metric, 0)
                results.append({**params, self.metric: m if np.isfinite(m) else -999})
            except Exception as e:
                results.append({**params, self.metric: -999})
        df = pd.DataFrame(results).sort_values(self.metric, ascending=False)
        best = df.iloc[0]
        return {k: best[k] for k in self.param_grid.keys()}, float(best[self.metric]), df

    def _test(self, params, test_data, benchmark_data):
        runner = VectorBTRunner(initial_capital=self.initial_capital, cost_model=self.cost_model)
        return runner.run(self.strategy_class(**params), test_data, benchmark_data)

    def _chain_equity(self, curves):
        if not curves: return pd.Series(dtype=float)
        result_vals, result_idx, cur = [], [], self.initial_capital
        for c in curves:
            if not len(c): continue
            scaled = c * (cur / c.iloc[0])
            result_vals.extend(scaled.tolist()); result_idx.extend(c.index.tolist())
            cur = scaled.iloc[-1]
        return pd.Series(result_vals, index=result_idx).sort_index()

    def _sharpe(self, equity):
        if len(equity) < 10: return 0.0
        ret = equity.pct_change().dropna()
        exc = ret - 0.065/252
        return float(exc.mean()/exc.std()*np.sqrt(252)) if exc.std() > 0 else 0.0

    def _param_stability(self, all_params):
        if not all_params: return 0.0
        scores = []
        for param in self.param_grid.keys():
            vals = [p.get(param) for p in all_params if p.get(param) is not None]
            if vals:
                most_common = max(set(vals), key=vals.count)
                scores.append(vals.count(most_common)/len(vals))
        return float(np.mean(scores)) if scores else 0.0

    def _most_common_params(self, all_params):
        if not all_params: return {}
        return {p: max((v.get(p) for v in all_params if v.get(p) is not None),
                       key=lambda x: sum(1 for v in all_params if v.get(p)==x))
                for p in self.param_grid.keys()}
