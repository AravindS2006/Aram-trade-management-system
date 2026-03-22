"""
Forward Test Runner - Aram-TMS
Connects strategies to DhanHQ Sandbox for paper trading sessions.
"""
from __future__ import annotations
import json
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd
from loguru import logger
from src.strategies.base_strategy import BaseStrategy
from src.forward_testing.dhan_sandbox import DhanSandboxClient
from src.data.yfinance_loader import YFinanceLoader
from src.risk.risk_manager import RiskManager


@dataclass
class ForwardTestSession:
    session_id: str; strategy_name: str; start_time: datetime
    symbols: List[str]; initial_capital: float; current_capital: float
    realized_pnl: float = 0.0; unrealized_pnl: float = 0.0
    total_trades: int = 0; winning_trades: int = 0; is_active: bool = True

    @property
    def total_pnl(self): return self.realized_pnl + self.unrealized_pnl
    @property
    def win_rate(self): return self.winning_trades/self.total_trades if self.total_trades else 0.0
    @property
    def duration_hours(self): return (datetime.now()-self.start_time).total_seconds()/3600


class ForwardTestRunner:
    """
    Run strategies in DhanHQ sandbox paper trading mode.
    Usage: runner = ForwardTestRunner(strategy); runner.start(symbols=["RELIANCE","TCS"])
    """
    def __init__(self, strategy: BaseStrategy, risk_manager: Optional[RiskManager] = None,
                 scan_interval_seconds: int = 60, data_interval: str = "5m",
                 capital: float = 1_000_000, max_positions: int = 5) -> None:
        self.strategy = strategy
        self.risk_manager = risk_manager or RiskManager()
        self.scan_interval = scan_interval_seconds
        self.data_interval = data_interval
        self.capital = capital
        self.max_positions = max_positions
        self.dhan = DhanSandboxClient()
        self.yf = YFinanceLoader()
        self._session: Optional[ForwardTestSession] = None
        self._stop_event = threading.Event()
        logger.info(f"ForwardTestRunner ready: {strategy}")

    def start(self, symbols: List[str], run_hours: Optional[float] = None,
              run_until_market_close: bool = True) -> ForwardTestSession:
        sid = datetime.now().strftime("FT_%Y%m%d_%H%M%S")
        self._session = ForwardTestSession(
            session_id=sid, strategy_name=self.strategy.NAME,
            start_time=datetime.now(), symbols=symbols,
            initial_capital=self.capital, current_capital=self.capital)
        logger.info(f"Session started: {sid} | {self.strategy} | {symbols}")
        self._stop_event.clear()
        t = threading.Thread(target=self._loop,
                             args=(symbols, run_hours, run_until_market_close), daemon=True)
        t.start()
        return self._session

    def stop(self) -> None:
        logger.info("Stopping forward test...")
        self._stop_event.set()
        if self._session: self._session.is_active = False
        self._close_all()
        self._save_results()

    def get_status(self) -> Optional[Dict[str, Any]]:
        if not self._session: return None
        dhan_status = self.dhan.get_status_summary()
        positions = self.dhan.get_positions()
        return {"session_id": self._session.session_id, "strategy": self._session.strategy_name,
                "duration_hours": round(self._session.duration_hours, 2),
                "total_trades": self._session.total_trades, "win_rate": self._session.win_rate,
                "total_pnl": self._session.total_pnl, "market_open": dhan_status.get("market_open"),
                "open_positions": len(positions)}

    def _loop(self, symbols, run_hours, run_until_market_close):
        start = datetime.now()
        while not self._stop_event.is_set():
            if run_hours and (datetime.now()-start).total_seconds()/3600 >= run_hours: break
            if run_until_market_close and not self.dhan.is_market_open(): break
            try: self._scan(symbols)
            except Exception as e: logger.error(f"Scan error: {e}")
            self._stop_event.wait(timeout=self.scan_interval)
        self._close_all()

    def _scan(self, symbols):
        lookback = (datetime.now()-timedelta(days=60)).strftime("%Y-%m-%d")
        today = datetime.now().strftime("%Y-%m-%d")
        positions = self.dhan.get_positions()
        held = set(positions["tradingSymbol"].tolist()) if not positions.empty and "tradingSymbol" in positions.columns else set()
        for sym in symbols:
            try:
                data = self.yf.fetch(f"{sym}.NS", start=lookback, end=today,
                                      interval=self.data_interval, use_cache=False)
                if data.empty or len(data) < 20: continue
                sig = int(self.strategy.generate_signals(data).iloc[-1])
                if sig == 1 and sym not in held: self._enter(sym, data)
                elif sig in (-1, 0) and sym in held: self.dhan.close_position(sym)
            except Exception as e:
                logger.warning(f"Signal error {sym}: {e}")

    def _enter(self, symbol: str, data: pd.DataFrame):
        price = float(data["Close"].iloc[-1])
        tr = pd.concat([data["High"]-data["Low"],
                        (data["High"]-data["Close"].shift(1)).abs(),
                        (data["Low"]-data["Close"].shift(1)).abs()], axis=1).max(axis=1)
        atr = float(tr.rolling(14).mean().iloc[-1])
        sl = self.strategy.get_stop_loss(price, 1, atr)
        tp = self.strategy.get_take_profit(price, 1, atr)
        funds = self.dhan.get_fund_limits()
        if funds.get("available_balance", 0) < price * 10: return
        positions = self.dhan.get_positions()
        if not positions.empty and len(positions) >= self.max_positions: return
        qty = self.strategy.get_position_size(self.capital, price, sl)
        if qty <= 0: return
        order = self.dhan.place_market_order(symbol, "BUY", qty, stop_loss=sl, take_profit=tp,
                                              strategy_name=self.strategy.NAME)
        if order and self._session:
            self._session.total_trades += 1
            logger.info(f"ENTERED {symbol} {qty}@~Rs.{price:.2f} SL={sl:.2f} TP={tp:.2f}")

    def _close_all(self):
        try:
            positions = self.dhan.get_positions()
            if positions.empty: return
            for _, p in positions.iterrows():
                sym = p.get("tradingSymbol","")
                if sym: self.dhan.close_position(sym); time.sleep(0.5)
        except Exception as e: logger.error(f"Close all error: {e}")

    def _save_results(self):
        if not self._session: return
        out = Path("data/results/forward_tests")
        out.mkdir(parents=True, exist_ok=True)
        d = {"session_id": self._session.session_id, "strategy": self._session.strategy_name,
             "start_time": self._session.start_time.isoformat(),
             "end_time": datetime.now().isoformat(),
             "symbols": self._session.symbols, "total_trades": self._session.total_trades,
             "total_pnl": self._session.total_pnl}
        with open(out / f"{self._session.session_id}.json", "w") as f:
            json.dump(d, f, indent=2)
        logger.info(f"Session saved: {self._session.session_id}")
