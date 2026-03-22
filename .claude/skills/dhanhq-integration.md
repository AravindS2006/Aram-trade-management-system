# Skill: DhanHQ Integration — Aram-TMS

## Authentication (.env)
```env
DHAN_SANDBOX_CLIENT_ID=your_sandbox_id
DHAN_SANDBOX_ACCESS_TOKEN=your_sandbox_token
DHAN_CLIENT_ID=your_live_id
DHAN_ACCESS_TOKEN=your_live_token
```

## Client Init
```python
from src.forward_testing.dhan_sandbox import DhanSandboxClient
sandbox = DhanSandboxClient()   # reads .env automatically
```

## Key API Operations
```python
# Market Order
order = dhan.place_order(
    security_id="1333", exchange_segment=dhan.NSE_EQ,
    transaction_type=dhan.BUY, quantity=100,
    order_type=dhan.MARKET, product_type=dhan.CNC, price=0
)
# Limit Order
order = dhan.place_order(..., order_type=dhan.LIMIT, price=2500.00)
# Stop Loss
order = dhan.place_order(..., order_type=dhan.SL, price=2450.0, trigger_price=2460.0)
# Holdings / Positions / Orders
holdings = dhan.get_holdings()
positions = dhan.get_positions()
orders = dhan.get_order_list()
funds = dhan.get_fund_limits()
```

## Exchange Segments
```python
NSE_EQ="NSE_EQ"   BSE_EQ="BSE_EQ"   NSE_FNO="NSE_FNO"
NSE_CURRENCY="NSE_CURRENCY"   MCX_COMM="MCX_COMM"
```

## ALWAYS Check Mode Before Trading
```python
if trading_mode == TradingMode.LIVE:
    confirm = input("Type CONFIRM_LIVE: ")
    if confirm != "CONFIRM_LIVE": raise RuntimeError("Not confirmed")
```

## Error Handling
```python
from dhanhq.exceptions import DhanAPIException
try:
    result = dhan.place_order(...)
except DhanAPIException as e:
    if e.error_code == "INSUFFICIENT_FUNDS": handle_margin_shortage()
    elif e.error_code == "RATE_LIMIT": time.sleep(1); retry()
    logger.error(f"DhanHQ error: {e}")
```
