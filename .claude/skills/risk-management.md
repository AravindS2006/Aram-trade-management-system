# Skill: Risk Management — Aram-TMS

## Risk Config (config/settings.yaml)
max_drawdown_stop: 0.15      # 15% portfolio drawdown halt
daily_loss_limit: 0.03       # 3% daily loss circuit breaker
max_open_positions: 20
max_sector_concentration: 0.30
max_single_stock_pct: 0.05
risk_per_trade: 0.01         # 1% per trade
min_rr_ratio: 2.0            # Minimum 2:1 reward:risk
max_order_value: 500000      # Rs.5L per order
consecutive_loss_halt: 5

## Using the Risk Manager
```python
from src.risk.risk_manager import RiskManager, RiskConfig
rm = RiskManager()
result = rm.validate_order(
    symbol="RELIANCE", quantity=100, price=2800.0, side="BUY",
    portfolio_value=1_000_000, stop_loss=2730.0, take_profit=2940.0
)
if not result.passed:
    print(result.reasons)
```

## Position Sizing
```python
# Fixed Fractional (default)
qty = rm.calculate_position_size(1_000_000, 2800.0, 2730.0, method="fixed_fractional")
# Kelly (use 25% fractional)
qty = rm.calculate_position_size(1_000_000, 2800.0, 2730.0, method="kelly", win_rate=0.55)
```

## Circuit Breakers (auto-triggered)
1. Daily loss >= 3% of portfolio
2. Portfolio drawdown >= 15%
3. 5 consecutive losing trades
4. F&O ban list violation
5. Order rate > 10/minute

## Indian Market Rules
- Check F&O ban list daily (NSE publishes every morning)
- Do not place orders at upper/lower circuit limits
- Reduce position size 2 days before earnings results
- Adjust F&O positions before weekly/monthly expiry (Thursday)
- Apply SEBI peak margin rules for intraday leverage
