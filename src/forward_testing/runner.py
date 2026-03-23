"""
Forward Test Runner - Aram-TMS
Connects strategies to DhanHQ Sandbox for paper trading sessions.
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger

from src.core.events import Event, EventBus, EventType
from src.data.yfinance_loader import YFinanceLoader
from src.forward_testing.dhan_sandbox import DhanSandboxClient
from src.notifications.trade_logger import TradeLogger
from src.portfolio.state import PortfolioState
from src.risk.risk_manager import RiskManager
from src.strategies.base_strategy import BaseStrategy


@dataclass
class ForwardTestSession:
    session_id: str
    strategy_name: str
    start_time: datetime
    symbols: list[str]
    initial_capital: float
    current_capital: float
    peak_capital: float
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    is_active: bool = True

    @property
    def total_pnl(self) -> float:
        return self.realized_pnl + self.unrealized_pnl

    @property
    def win_rate(self) -> float:
        return self.winning_trades / self.total_trades if self.total_trades else 0.0

    @property
    def duration_hours(self) -> float:
        return (datetime.now() - self.start_time).total_seconds() / 3600


class ForwardTestRunner:
    """
    Run strategies in DhanHQ sandbox paper trading mode.
    Usage: runner = ForwardTestRunner(strategy); runner.start(symbols=["RELIANCE","TCS"])
    """

    def __init__(
        self,
        strategy: BaseStrategy,
        risk_manager: RiskManager | None = None,
        scan_interval_seconds: int = 60,
        data_interval: str = "5m",
        capital: float = 1_000_000,
        max_positions: int = 5,
    ) -> None:
        self.strategy = strategy
        self.risk_manager = risk_manager or RiskManager()
        self.scan_interval = scan_interval_seconds
        self.data_interval = data_interval
        self.capital = capital
        self.max_positions = max_positions
        self.dhan = DhanSandboxClient()
        self.yf = YFinanceLoader()
        self.event_bus = EventBus()
        self.portfolio_state = PortfolioState()
        self.trade_logger = TradeLogger()
        self._session: ForwardTestSession | None = None
        self._stop_event = threading.Event()
        self._status_path: Path | None = None
        self._register_event_handlers()
        logger.info(f"ForwardTestRunner ready: {strategy}")

    def _register_event_handlers(self) -> None:
        self.event_bus.subscribe(EventType.SIGNAL, self._log_event)
        self.event_bus.subscribe(EventType.ORDER_REJECTED, self._log_event)
        self.event_bus.subscribe(EventType.ORDER_PLACED, self._log_event)
        self.event_bus.subscribe(EventType.RISK_BREACH, self._log_event)

    def _log_event(self, event: Event) -> None:
        logger.info(f"{event.event_type.value.upper()} | {event.source} | {event.payload}")

    def start(
        self,
        symbols: list[str],
        run_hours: float | None = None,
        run_until_market_close: bool = True,
    ) -> ForwardTestSession:
        sid = datetime.now().strftime("FT_%Y%m%d_%H%M%S")
        self._session = ForwardTestSession(
            session_id=sid,
            strategy_name=self.strategy.NAME,
            start_time=datetime.now(),
            symbols=symbols,
            initial_capital=self.capital,
            current_capital=self.capital,
            peak_capital=self.capital,
        )
        out = Path("data/results/forward_tests")
        out.mkdir(parents=True, exist_ok=True)
        self._status_path = out / f"{sid}_status.json"
        logger.info(f"Session started: {sid} | {self.strategy} | {symbols}")
        self._stop_event.clear()
        t = threading.Thread(
            target=self._loop, args=(symbols, run_hours, run_until_market_close), daemon=True
        )
        t.start()
        return self._session

    def stop(self) -> None:
        logger.info("Stopping forward test...")
        self._stop_event.set()
        if self._session:
            self._session.is_active = False
        self._close_all()
        self._save_results()

    def get_status(self) -> dict[str, Any] | None:
        if not self._session:
            return None
        dhan_status = self.dhan.get_status_summary()
        return {
            "session_id": self._session.session_id,
            "strategy": self._session.strategy_name,
            "duration_hours": round(self._session.duration_hours, 2),
            "total_trades": self._session.total_trades,
            "win_rate": self._session.win_rate,
            "total_pnl": self._session.total_pnl,
            "market_open": dhan_status.get("market_open"),
            "open_positions": len(self.portfolio_state.positions),
            "risk": self.risk_manager.get_status(),
            "portfolio": self.portfolio_state.as_dict(),
        }

    def _loop(self, symbols, run_hours, run_until_market_close):
        start = datetime.now()
        while not self._stop_event.is_set():
            if run_hours and (datetime.now() - start).total_seconds() / 3600 >= run_hours:
                break
            if run_until_market_close and not self.dhan.is_market_open():
                break
            try:
                self._scan(symbols)
                self._persist_status()
            except Exception as e:
                logger.error(f"Scan error: {e}")
            self._stop_event.wait(timeout=self.scan_interval)
        self._close_all()

    def _scan(self, symbols: list[str]) -> None:
        lookback = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
        today = datetime.now().strftime("%Y-%m-%d")
        positions = self.dhan.get_positions()
        self.portfolio_state.sync_from_positions_df(positions)
        held = set(self.portfolio_state.positions.keys())
        self._refresh_pnl_from_positions()
        if self._session:
            dd_result = self.risk_manager.validate_portfolio_drawdown(
                portfolio_value=self._session.current_capital,
                peak_value=max(self._session.peak_capital, self._session.current_capital),
            )
            if not dd_result.passed:
                self.event_bus.emit(
                    Event(
                        event_type=EventType.RISK_BREACH,
                        source="forward_runner",
                        payload={"reasons": dd_result.reasons},
                    )
                )
                return

        for sym in symbols:
            try:
                data = self.yf.fetch(
                    f"{sym}.NS",
                    start=lookback,
                    end=today,
                    interval=self.data_interval,
                    use_cache=False,
                )
                if data.empty or len(data) < 20:
                    continue
                sig = int(self.strategy.generate_signals(data).iloc[-1])
                self.event_bus.emit(
                    Event(
                        event_type=EventType.SIGNAL,
                        source=self.strategy.NAME,
                        payload={"symbol": sym, "signal": sig},
                    )
                )
                if sig == 1 and sym not in held:
                    self._enter(sym, data)
                elif sig in (-1, 0) and sym in held:
                    qty = self.portfolio_state.get_position_qty(sym)
                    exit_px = float(data["Close"].iloc[-1])
                    self.dhan.close_position(sym)
                    if self._session:
                        self.trade_logger.log_order(
                            session_id=self._session.session_id,
                            symbol=sym,
                            side="SELL",
                            quantity=abs(qty),
                            price=exit_px,
                            status="CLOSE_REQUESTED",
                            mode="forward_test",
                            strategy=self.strategy.NAME,
                            timeframe=self.data_interval,
                            data_source="yfinance",
                            portfolio_value=self._session.current_capital,
                            metadata={"signal": sig},
                        )
                    self.event_bus.emit(
                        Event(
                            event_type=EventType.ORDER_CLOSED,
                            source="forward_runner",
                            payload={"symbol": sym},
                        )
                    )
            except Exception as e:
                logger.warning(f"Signal error {sym}: {e}")

    def _enter(self, symbol: str, data: pd.DataFrame) -> None:
        price = float(data["Close"].iloc[-1])
        tr = pd.concat(
            [
                data["High"] - data["Low"],
                (data["High"] - data["Close"].shift(1)).abs(),
                (data["Low"] - data["Close"].shift(1)).abs(),
            ],
            axis=1,
        ).max(axis=1)
        atr = float(tr.rolling(14).mean().iloc[-1])
        sl = self.strategy.get_stop_loss(price, 1, atr)
        tp = self.strategy.get_take_profit(price, 1, atr)
        funds = self.dhan.get_fund_limits()
        if funds.get("available_balance", 0) < price * 10:
            return
        positions = self.dhan.get_positions()
        if not positions.empty and len(positions) >= self.max_positions:
            return
        qty = self.strategy.get_position_size(self.capital, price, sl)
        if qty <= 0 or not self._session:
            return

        risk_result = self.risk_manager.validate_order(
            symbol=symbol,
            quantity=qty,
            price=price,
            side="BUY",
            portfolio_value=max(self._session.current_capital, 1.0),
            open_positions=len(self.portfolio_state.positions),
            stop_loss=sl,
            take_profit=tp,
        )
        if not risk_result.passed:
            reason = "; ".join(risk_result.reasons)
            self.trade_logger.log_order(
                session_id=self._session.session_id,
                symbol=symbol,
                side="BUY",
                quantity=qty,
                price=price,
                status="BLOCKED",
                reason=reason,
                mode="forward_test",
                strategy=self.strategy.NAME,
                timeframe=self.data_interval,
                data_source="yfinance",
                stop_loss=sl,
                take_profit=tp,
                portfolio_value=self._session.current_capital,
                risk_reasons=risk_result.reasons,
                metadata={"stop_loss": sl, "take_profit": tp},
            )
            self.event_bus.emit(
                Event(
                    event_type=EventType.ORDER_REJECTED,
                    source="risk_manager",
                    payload={"symbol": symbol, "reason": risk_result.reasons},
                )
            )
            return

        order = self.dhan.place_market_order(
            symbol, "BUY", qty, stop_loss=sl, take_profit=tp, strategy_name=self.strategy.NAME
        )
        if order:
            self._session.total_trades += 1
            self.trade_logger.log_order(
                session_id=self._session.session_id,
                symbol=symbol,
                side="BUY",
                quantity=qty,
                price=price,
                status="PLACED",
                mode="forward_test",
                strategy=self.strategy.NAME,
                order_id=str(order.order_id or ""),
                timeframe=self.data_interval,
                data_source="yfinance",
                stop_loss=sl,
                take_profit=tp,
                portfolio_value=self._session.current_capital,
                metadata={"stop_loss": sl, "take_profit": tp, "strategy": self.strategy.NAME},
            )
            self.event_bus.emit(
                Event(
                    event_type=EventType.ORDER_PLACED,
                    source="forward_runner",
                    payload={"symbol": symbol, "quantity": qty, "price": price},
                )
            )
            logger.info(f"ENTERED {symbol} {qty}@~Rs.{price:.2f} SL={sl:.2f} TP={tp:.2f}")

    def _refresh_pnl_from_positions(self) -> None:
        if not self._session:
            return
        upnl = self.portfolio_state.total_unrealized_pnl()
        self._session.unrealized_pnl = upnl
        self._session.current_capital = (
            self._session.initial_capital + self._session.realized_pnl + upnl
        )
        self._session.peak_capital = max(self._session.peak_capital, self._session.current_capital)

    def _close_all(self):
        try:
            positions = self.dhan.get_positions()
            if positions.empty:
                return
            for _, p in positions.iterrows():
                sym = p.get("tradingSymbol", "")
                if sym:
                    self.dhan.close_position(sym)
                    time.sleep(0.5)
        except Exception as e:
            logger.error(f"Close all error: {e}")

    def _persist_status(self) -> None:
        if not self._status_path:
            return
        status = self.get_status() or {}
        status["timestamp"] = datetime.now().isoformat(timespec="seconds")
        with self._status_path.open("w", encoding="utf-8") as fp:
            json.dump(status, fp, indent=2)

    def _save_results(self):
        if not self._session:
            return
        out = Path("data/results/forward_tests")
        out.mkdir(parents=True, exist_ok=True)
        d = {
            "session_id": self._session.session_id,
            "strategy": self._session.strategy_name,
            "start_time": self._session.start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "symbols": self._session.symbols,
            "total_trades": self._session.total_trades,
            "win_rate": self._session.win_rate,
            "total_pnl": self._session.total_pnl,
            "ending_capital": self._session.current_capital,
        }
        with open(out / f"{self._session.session_id}.json", "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2)
        logger.info(f"Session saved: {self._session.session_id}")
