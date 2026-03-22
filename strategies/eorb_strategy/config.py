"""Configuration constants for the Enhanced Opening Range Breakout (E-ORB) strategy."""

from datetime import time

# ── Opening Range ────────────────────────────────────────────────────────────
ORB_WINDOW_START = time(9, 15)
ORB_WINDOW_END = time(9, 30)
BREAKOUT_TF = "5min"
ORB_MIN_RANGE_PCT = 0.20
ORB_MAX_RANGE_PCT = 2.50
ORB_BUFFER_PCT = 0.0005  # 0.05% as decimal

# ── ADX Settings ─────────────────────────────────────────────────────────────
ADX_PERIOD = 14
ADX_MIN_THRESHOLD = 25
ADX_STRONG = 35
DI_CONFIRM = True

# ── EMA Settings ─────────────────────────────────────────────────────────────
EMA_FAST = 9
EMA_SLOW = 21

# ── VWAP Settings ────────────────────────────────────────────────────────────
VWAP_SESSION_RESET = time(9, 15)
VWAP_BAND_STD = 1.0

# ── Volume Filter ────────────────────────────────────────────────────────────
RVOL_LOOKBACK = 20
RVOL_MIN = 1.5

# ── Session Time Rules ───────────────────────────────────────────────────────
NO_TRADE_OPEN = time(9, 15)
ENTRY_WINDOW_START = time(9, 30)
ENTRY_WINDOW_END = time(14, 0)
LUNCH_BLACKOUT_START = time(11, 30)
LUNCH_BLACKOUT_END = time(13, 0)
HARD_EXIT_TIME = time(15, 15)
LATE_ENTRY_CUTOFF = time(13, 30)
LATE_EXIT_TIME = time(14, 30)
AVOID_EXPIRY_DAY = True  # Skip Thursday (weekly F&O expiry)

# ── India VIX Pre-filter ─────────────────────────────────────────────────────
VIX_MAX = 22.0
VIX_MIN = 10.0
VIX_USE_PREV_CLOSE = True
VIX_DEFAULT_BACKTEST = 14.5  # Fixed VIX for backtesting without live data

# ── Risk Management ──────────────────────────────────────────────────────────
CAPITAL = 500_000
RISK_PER_TRADE_PCT = 0.005
MAX_DAILY_LOSS_PCT = 0.015
MAX_DAILY_TRADES = 3
COMMISSION_PCT = 0.0003
SLIPPAGE_PCT = 0.0002
MAX_POSITION_PCT = 0.15  # 15% cap per trade

# ── Targets and Exits ────────────────────────────────────────────────────────
SL_BUFFER_PCT = 0.0010  # 0.10% as decimal
TARGET1_RR = 1.5
TARGET1_CLOSE_PCT = 0.50
TARGET2_RR = 2.5
TRAIL_EMA_BUFFER = 0.002  # 0.2% EMA trailing buffer
BREAKEVEN_AT_T1 = True

# ── ATR Alternative Stop ─────────────────────────────────────────────────────
ATR_SL_MULTIPLIER = 1.5

# ── Signal Scoring Thresholds ────────────────────────────────────────────────
SCORE_A_MIN = 10   # Full size, target 2.5x range
SCORE_B_MIN = 7    # Full size, target 2.0x range
SCORE_C_MIN = 5    # 50% size, target 1.5x range
SCORE_SKIP = 5     # Below this → skip

# ── Instrument Universe ──────────────────────────────────────────────────────
UNIVERSE = [
    "RELIANCE", "HDFCBANK", "INFY", "TCS", "ICICIBANK",
    "KOTAKBANK", "LT", "AXISBANK", "SBIN", "BAJFINANCE",
    "BHARTIARTL", "ASIANPAINT", "MARUTI", "TITAN", "WIPRO",
    "BANKNIFTY", "NIFTY",
]
PRIORITY_SYMBOLS = ["BANKNIFTY", "NIFTY", "RELIANCE", "HDFCBANK", "INFY"]

# ── Session Constants ────────────────────────────────────────────────────────
BARS_PER_SESSION_5M = 75  # ~6.25 hours of 5-min bars
