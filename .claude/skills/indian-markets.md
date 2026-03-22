# Skill: Indian Markets — Aram-TMS

## Market Hours (IST)
| Session | Time |
|---|---|
| Pre-Open Entry | 9:00–9:08 AM |
| Normal Trading | 9:15 AM–3:30 PM |
| Post-Close | 3:40–4:00 PM |

## yFinance Symbols
Append .NS for NSE, .BO for BSE:
RELIANCE.NS  TCS.NS  HDFCBANK.NS  INFY.NS  ICICIBANK.NS
KOTAKBANK.NS  LT.NS  SBIN.NS  BHARTIARTL.NS  AXISBANK.NS
Indices: ^NSEI (NIFTY50)  ^NSEBANK (BankNifty)  ^BSESN (SENSEX)

## Transaction Costs
```python
# Equity Delivery
brokerage=0,  stt_sell=0.001,  exchange=0.0000345
dp_charges=15.93,  gst=0.18 (on brokerage+exchange),  stamp_buy=0.00015

# Equity Intraday
brokerage=20,  stt_sell=0.00025,  stamp_buy=0.00003

# Futures
brokerage=20,  stt_sell=0.0001,  exchange=0.0000019
```

## F&O Key Info
```python
WEEKLY_EXPIRY = "Thursday"   MONTHLY_EXPIRY = "last_Thursday"
LOT_SIZES = {"NIFTY":50, "BANKNIFTY":15, "FINNIFTY":40}
STRIKE_INTERVALS = {"NIFTY":50, "BANKNIFTY":100}
```

## Sectors (NIFTY 50)
Financial: HDFCBANK ICICIBANK KOTAKBANK AXISBANK SBIN BAJFINANCE
IT: TCS INFY HCLTECH WIPRO TECHM
Energy: RELIANCE ONGC BPCL COALINDIA
Consumer: HINDUNILVR ITC NESTLEIND TITAN ASIANPAINT
Auto: MARUTI TATAMOTORS M&M EICHERMOT HEROMOTOCO BAJAJ-AUTO
Pharma: SUNPHARMA CIPLA DRREDDY DIVISLAB APOLLOHOSP

## Data Validation Rules
1. Remove weekends and NSE holidays
2. High >= Low, High >= Close, Low <= Close
3. Close > 0, Volume >= 0
4. No gaps > 5 trading days
5. Flag >50% single-day moves (unadjusted corporate actions)
6. Forward-fill max 3 days only
