---
name: debug-portfolio
description: "Trace portfolio state changes through a backtest. Diagnose NAV calculation errors, position tracking issues, and trade execution problems."
argument-hint: "<strategy-file> [bar-range: 1-100] [detail-level: summary|detailed|verbose]"
---

# Debug Portfolio Prompt

Trace and diagnose portfolio state changes during backtest execution.

## Usage

```
/debug-portfolio intraday_momentum_strategy.py --bar-range 1-50 --detail-level verbose
```

## Debug Output Example

### Summary View
```
Bar  Signal  Price   Trade Type  Qty   Entry      Exit      P&L        NAV
────────────────────────────────────────────────────────────────────────────
1      0     100.50  -           -     -          -         -          100,000
2     +1     101.20  OPEN LONG   10    101.20     -         -          99,988
3      0     102.50  -           -     -          -         +130       100,118
...
45    -1     95.10   CLOSE LONG  10    101.20    95.10     -600        99,488
```

### Detailed View
```
┌─ BAR 45 ────────────────────────────────────────────┐
│ Time: 2023-01-15 10:30:00                          │
│ Price: 95.10 (O:95.20, H:96.30, L:94.90, C:95.10) │
│ Signal: -1 (SELL)                                  │
├─ PORTFOLIO STATE BEFORE ──────────────────────────┤
│ Cash: 99,988.00                                    │
│ Positions:                                         │
│   STOCK: qty=10, entry=101.20, value=951.00       │
│ Total NAV: 100,939.00                             │
├─ TRADE EXECUTION ─────────────────────────────────┤
│ Action: CLOSE LONG                                │
│ Quantity: 10 shares                               │
│ Exit Price: 95.10                                 │
│ Proceeds: 951.00                                  │
│ Commission: -14.27 (1.5% of proceeds)            │
│ Net Cash In: +936.73                              │
├─ PORTFOLIO STATE AFTER ───────────────────────────┤
│ Cash: 100,924.73                                  │
│ Positions:                                        │
│   STOCK: qty=0 (CLOSED)                           │
│ Total NAV: 100,924.73                             │
├─ TRADE RESULT ────────────────────────────────────┤
│ Entry: 101.20                                     │
│ Exit: 95.10                                       │
│ Shares: 10                                        │
│ Gross P&L: -610.00 (loss)                        │
│ Net P&L: -624.27 (including commission)          │
│ Return: -0.62%                                    │
└────────────────────────────────────────────────────┘
```

### Verbose View (with calculations)
```
BAR 45 Calculation Details:

Signal generation:
  SMA20 = 94.50
  Price = 95.10
  Price > SMA20? YES → Signal = 0 (no trade expected)
  Actual signal received: -1 (CONFLICT!)

Trade execution invoked despite no signal - BUG FOUND!

Call stack:
  on_signal(signal=-1, price=95.10)
  portfolio.close_position('STOCK')
  
Expected: Signal generation should precede trade execution
Actual: Trade executed manually

Fix: Remove manual on_signal() call; rely on generate_signals()
```

## Diagnostic Checks Performed

- ✓ Signal validity (0, +1, -1 only)
- ✓ Trade execution timing (signal → execution)
- ✓ Portfolio invariants (NAV = cash + positions)
- ✓ Price validity (>0, within OHLC range)
- ✓ Position tracking (correct quantities)
- ✓ Cost application (commissions, slippage)
- ✓ Return calculation (matches NAV changes)

## Common Issues Found

| Issue | Symptom | Root Cause |
|-------|---------|-----------|
| Flat returns | NAV constant despite trades | Positions not updating |
| Negative NAV | Portfolio value < 0 | Costs applied multiple times |
| Missing trades | Fewer trades than expected | Signal generation skipped |
| Wrong entry price | Trade at wrong price | Using wrong data point |

