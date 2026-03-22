"""
DhanHQ Sandbox Client - Aram-TMS
Paper trading via DhanHQ sandbox. No real money.
"""
from __future__ import annotations
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd
from dotenv import load_dotenv
from loguru import logger
try:
    from dhanhq import dhanhq
    DHAN_AVAILABLE = True
except ImportError:
    DHAN_AVAILABLE = False
    logger.warning("dhanhq not installed: pip install dhanhq")
load_dotenv()


class OrderStatus(Enum):
    PENDING="PENDING"; OPEN="OPEN"; FILLED="FILLED"
    CANCELLED="CANCELLED"; REJECTED="REJECTED"


@dataclass
class Order:
    order_id: Optional[str]; symbol: str; security_id: str
    exchange_segment: str; side: str; quantity: int
    order_type: str; product_type: str; price: float
    trigger_price: float = 0.0; status: OrderStatus = OrderStatus.PENDING
    filled_qty: int = 0; avg_fill_price: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    stop_loss: Optional[float] = None; take_profit: Optional[float] = None
    strategy_name: Optional[str] = None

    @property
    def is_filled(self): return self.status == OrderStatus.FILLED
    @property
    def trade_value(self): return self.avg_fill_price * self.filled_qty


class DhanSecurityMaster:
    """Maps NSE symbols to DhanHQ security IDs."""
    _MAP = {
        "NSE_EQ": {
            "RELIANCE":"1333","TCS":"11536","INFY":"1594","HDFCBANK":"1333",
            "HINDUNILVR":"1394","ICICIBANK":"4963","KOTAKBANK":"1922","LT":"11483",
            "SBIN":"3045","BHARTIARTL":"10604","AXISBANK":"5900","ITC":"1660",
            "ASIANPAINT":"236","MARUTI":"10999","HCLTECH":"7229","SUNPHARMA":"3351",
            "TITAN":"3506","WIPRO":"3787","NESTLEIND":"17963","BAJFINANCE":"317",
        }
    }
    def __init__(self, master_file: Optional[str] = None):
        self._master_df: Optional[pd.DataFrame] = None
        if master_file and Path(master_file).exists():
            try:
                self._master_df = pd.read_csv(master_file)
                logger.info(f"DhanHQ master loaded: {len(self._master_df)} securities")
            except Exception as e:
                logger.warning(f"Master load failed: {e}")

    def get_security_id(self, symbol: str, exchange_segment: str = "NSE_EQ") -> Optional[str]:
        if self._master_df is not None:
            mask = self._master_df.get("SEM_TRADING_SYMBOL","") == symbol
            matches = self._master_df[mask]
            if not matches.empty:
                return str(matches.iloc[0].get("SEM_SMST_SECURITY_ID",""))
        return self._MAP.get(exchange_segment,{}).get(symbol.upper())


class DhanSandboxClient:
    """
    DhanHQ Sandbox client for paper trading forward tests.
    Set DHAN_SANDBOX_CLIENT_ID and DHAN_SANDBOX_ACCESS_TOKEN in .env
    """
    def __init__(self, client_id: Optional[str] = None, access_token: Optional[str] = None):
        self.client_id = client_id or os.getenv("DHAN_SANDBOX_CLIENT_ID","")
        self.access_token = access_token or os.getenv("DHAN_SANDBOX_ACCESS_TOKEN","")
        if not self.client_id or not self.access_token:
            raise ValueError("Set DHAN_SANDBOX_CLIENT_ID and DHAN_SANDBOX_ACCESS_TOKEN in .env")
        if not DHAN_AVAILABLE:
            raise ImportError("pip install dhanhq")
        self.dhan = dhanhq(self.client_id, self.access_token)
        self.master = DhanSecurityMaster()
        self._orders: Dict[str, Order] = {}
        logger.info(f"DhanHQ Sandbox connected: {self.client_id[:6]}***")

    def place_market_order(self, symbol: str, side: str, quantity: int,
                           product_type: str = "CNC", exchange_segment: str = "NSE_EQ",
                           stop_loss: Optional[float] = None, take_profit: Optional[float] = None,
                           strategy_name: Optional[str] = None) -> Optional[Order]:
        sec_id = self.master.get_security_id(symbol, exchange_segment)
        if not sec_id:
            logger.error(f"Security ID not found: {symbol}")
            return None
        try:
            dhan_side = self.dhan.BUY if side.upper()=="BUY" else self.dhan.SELL
            resp = self.dhan.place_order(
                security_id=sec_id, exchange_segment=getattr(self.dhan, exchange_segment, self.dhan.NSE),
                transaction_type=dhan_side, quantity=quantity,
                order_type=self.dhan.MARKET, product_type=getattr(self.dhan, product_type, self.dhan.CNC), price=0)
            if resp and resp.get("status") == "success":
                oid = resp.get("data",{}).get("orderId","")
                order = Order(order_id=oid, symbol=symbol, security_id=sec_id,
                              exchange_segment=exchange_segment, side=side.upper(),
                              quantity=quantity, order_type="MARKET", product_type=product_type,
                              price=0, stop_loss=stop_loss, take_profit=take_profit,
                              strategy_name=strategy_name)
                self._orders[oid] = order
                logger.info(f"Order placed: {side} {quantity} {symbol} | ID:{oid}")
                return order
            logger.error(f"Order failed: {resp}")
        except Exception as e:
            logger.error(f"Order exception: {e}")
        return None

    def cancel_order(self, order_id: str) -> bool:
        try:
            resp = self.dhan.cancel_order(order_id)
            if resp and resp.get("status") == "success":
                if order_id in self._orders: self._orders[order_id].status = OrderStatus.CANCELLED
                return True
        except Exception as e:
            logger.error(f"Cancel failed: {e}")
        return False

    def close_position(self, symbol: str, exchange_segment: str = "NSE_EQ") -> Optional[Order]:
        positions = self.get_positions()
        if positions.empty: return None
        if "tradingSymbol" not in positions.columns: return None
        pos = positions[positions["tradingSymbol"] == symbol]
        if pos.empty: return None
        qty = int(pos.iloc[0].get("netQty", 0))
        if qty == 0: return None
        side = "SELL" if qty > 0 else "BUY"
        return self.place_market_order(symbol, side, abs(qty), exchange_segment=exchange_segment)

    def get_holdings(self) -> pd.DataFrame:
        try:
            r = self.dhan.get_holdings()
            if r and r.get("status")=="success":
                d = r.get("data",[])
                return pd.DataFrame(d) if d else pd.DataFrame()
        except Exception as e: logger.error(f"Holdings error: {e}")
        return pd.DataFrame()

    def get_positions(self) -> pd.DataFrame:
        try:
            r = self.dhan.get_positions()
            if r and r.get("status")=="success":
                d = r.get("data",[])
                return pd.DataFrame(d) if d else pd.DataFrame()
        except Exception as e: logger.error(f"Positions error: {e}")
        return pd.DataFrame()

    def get_order_book(self) -> pd.DataFrame:
        try:
            r = self.dhan.get_order_list()
            if r and r.get("status")=="success":
                d = r.get("data",[])
                return pd.DataFrame(d) if d else pd.DataFrame()
        except Exception as e: logger.error(f"Orders error: {e}")
        return pd.DataFrame()

    def get_fund_limits(self) -> Dict[str, float]:
        try:
            r = self.dhan.get_fund_limits()
            if r and r.get("status")=="success":
                d = r.get("data",{})
                return {"available_balance": float(d.get("availabelBalance",0)),
                        "used_margin": float(d.get("utilizedAmount",0)),
                        "total_balance": float(d.get("sodLimit",0))}
        except Exception as e: logger.error(f"Funds error: {e}")
        return {}

    def get_ltp(self, symbol: str, exchange_segment: str = "NSE_EQ") -> Optional[float]:
        sec_id = self.master.get_security_id(symbol, exchange_segment)
        if not sec_id: return None
        try:
            r = self.dhan.ohlc_data(security_id=sec_id, exchange_segment=exchange_segment, instrument_type="EQUITY")
            if r and r.get("status")=="success":
                return float(r.get("data",{}).get("last_price",0))
        except Exception: pass
        return None

    def is_market_open(self) -> bool:
        now = datetime.now()
        if now.weekday() >= 5: return False
        return now.replace(hour=9,minute=15) <= now <= now.replace(hour=15,minute=30)

    def get_status_summary(self) -> Dict[str, Any]:
        funds = self.get_fund_limits()
        return {"market_open": self.is_market_open(),
                "available_balance": funds.get("available_balance",0),
                "timestamp": datetime.now().isoformat()}
