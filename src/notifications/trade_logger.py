"""Trade audit logger for forward/live sessions."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


class TradeLogger:
    REQUIRED_COLUMNS = [
        "timestamp",
        "session_id",
        "mode",
        "strategy",
        "symbol",
        "side",
        "quantity",
        "price",
        "order_value",
        "status",
        "reason",
        "order_id",
        "timeframe",
        "data_source",
        "stop_loss",
        "take_profit",
        "portfolio_value",
        "risk_reasons",
        "metadata",
    ]

    def __init__(self, base_dir: str | Path = "logs/trades") -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def log_order(
        self,
        session_id: str,
        symbol: str,
        side: str,
        quantity: int,
        price: float,
        status: str,
        reason: str = "",
        mode: str = "forward_test",
        strategy: str = "",
        order_id: str = "",
        timeframe: str = "",
        data_source: str = "",
        stop_loss: float | None = None,
        take_profit: float | None = None,
        portfolio_value: float | None = None,
        risk_reasons: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        day = datetime.now().strftime("%Y%m%d")
        path = self.base_dir / f"{session_id}_{day}.csv"
        metadata = metadata or {}
        row = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "session_id": session_id,
            "mode": mode,
            "strategy": strategy,
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": price,
            "order_value": float(quantity) * float(price),
            "status": status,
            "reason": reason,
            "order_id": order_id,
            "timeframe": timeframe,
            "data_source": data_source,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "portfolio_value": portfolio_value,
            "risk_reasons": json.dumps(risk_reasons or [], ensure_ascii=True),
            "metadata": json.dumps(metadata, ensure_ascii=True),
        }
        df = pd.DataFrame([row], columns=self.REQUIRED_COLUMNS)
        if path.exists():
            df.to_csv(path, mode="a", header=False, index=False)
        else:
            df.to_csv(path, index=False)
