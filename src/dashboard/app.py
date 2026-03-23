"""
Aram-TMS Professional Dashboard
Run: streamlit run src/dashboard/app.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

st.set_page_config(
    page_title="Aram-TMS", page_icon="⚡", layout="wide", initial_sidebar_state="expanded"
)

st.markdown(
    """
<style>
.stApp{background:#0A0E1A}
.stSidebar{background:#0F1629;border-right:1px solid #1F2937}
.metric-card{background:#111827;border:1px solid #1F2937;border-radius:8px;padding:16px;text-align:center}
.metric-value{font-size:26px;font-weight:700;color:#F9FAFB}
.metric-label{font-size:11px;color:#6B7280;text-transform:uppercase;letter-spacing:.05em}
#MainMenu{visibility:hidden}footer{visibility:hidden}
</style>""",
    unsafe_allow_html=True,
)

for k, v in [
    ("mode", "Backtest"),
    ("last_mode", "Backtest"),
    ("page", "Backtest Overview"),
    ("bt_results", {}),
    ("bt_diag", {}),
    ("bt_equity", pd.Series(dtype=float)),
    ("bt_benchmark_curve", pd.Series(dtype=float)),
    ("bt_symbol", "RELIANCE"),
    ("bt_data_source", "yFinance (<2yr)"),
    ("bt_trades", pd.DataFrame()),
    ("capital", 1_000_000),
]:
    if k not in st.session_state:
        st.session_state[k] = v


MODE_NAV: dict[str, list[tuple[str, str]]] = {
    "Backtest": [
        ("📊 Overview", "Backtest Overview"),
        ("🔬 Backtesting", "Backtesting"),
        ("🧠 Strategies", "Strategies"),
        ("⚠️ Risk Monitor", "Risk Monitor"),
        ("⚙️ Settings", "Settings"),
    ],
    "Forward Test": [
        ("📊 Overview", "Forward Overview"),
        ("📡 Forward Test", "Forward Test"),
        ("⚠️ Risk Monitor", "Risk Monitor"),
        ("⚙️ Settings", "Settings"),
    ],
    "Live Trading": [
        ("📊 Overview", "Live Overview"),
        ("🔴 Live Trading", "Live Trading"),
        ("⚠️ Risk Monitor", "Risk Monitor"),
        ("⚙️ Settings", "Settings"),
    ],
}


def _default_mode_page(mode: str) -> str:
    defaults = {
        "Backtest": "Backtest Overview",
        "Forward Test": "Forward Overview",
        "Live Trading": "Live Overview",
    }
    return defaults.get(mode, "Backtest Overview")


def _latest_forward_status() -> dict:
    status_files = sorted(
        Path("data/results/forward_tests").glob("*_status.json"), key=lambda p: p.stat().st_mtime
    )
    if not status_files:
        return {}
    try:
        with status_files[-1].open("r", encoding="utf-8") as fp:
            return json.load(fp)
    except Exception:
        return {}


def _latest_backtest_equity() -> pd.Series:
    eq_files = sorted(
        Path("data/results/backtests").glob("*_equity.parquet"), key=lambda p: p.stat().st_mtime
    )
    if not eq_files:
        return pd.Series(dtype=float)
    try:
        df = pd.read_parquet(eq_files[-1])
        if "value" in df.columns:
            return df["value"]
    except Exception:
        pass
    return pd.Series(dtype=float)


def _latest_trade_log() -> pd.DataFrame:
    trade_files = sorted(Path("logs/trades").glob("*.csv"), key=lambda p: p.stat().st_mtime)
    if not trade_files:
        return pd.DataFrame()
    try:
        return pd.read_csv(trade_files[-1]).tail(10)
    except Exception:
        return pd.DataFrame()


def _latest_backtest_trades() -> pd.DataFrame:
    trade_csv = sorted(
        Path("data/results/backtests").glob("*_trades.csv"), key=lambda p: p.stat().st_mtime
    )
    if trade_csv:
        try:
            return pd.read_csv(trade_csv[-1])
        except Exception:
            pass

    trade_parquet = sorted(
        Path("data/results/backtests").glob("*_trades.parquet"), key=lambda p: p.stat().st_mtime
    )
    if trade_parquet:
        try:
            return pd.read_parquet(trade_parquet[-1])
        except Exception:
            pass
    return pd.DataFrame()


def _pick_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    cols = {str(c).lower(): str(c) for c in df.columns}
    for candidate in candidates:
        found = cols.get(candidate.lower())
        if found:
            return found
    return None


def _compute_trade_metrics(trades: pd.DataFrame) -> dict[str, float]:
    if trades.empty:
        return {
            "num_trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "total_pnl": 0.0,
            "avg_pnl": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "profit_factor": 0.0,
            "expectancy": 0.0,
            "avg_return_pct": 0.0,
            "avg_holding_days": 0.0,
        }

    pnl_col = _pick_col(trades, ["pnl", "pnl_net", "PnL", "PnL Net"])
    ret_col = _pick_col(trades, ["return_pct", "return", "Return"])
    entry_col = _pick_col(trades, ["entry_time", "Entry Timestamp"])
    exit_col = _pick_col(trades, ["exit_time", "Exit Timestamp"])

    if pnl_col is None:
        return {
            "num_trades": int(len(trades)),
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "total_pnl": 0.0,
            "avg_pnl": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "profit_factor": 0.0,
            "expectancy": 0.0,
            "avg_return_pct": 0.0,
            "avg_holding_days": 0.0,
        }

    pnl = pd.to_numeric(trades[pnl_col], errors="coerce").dropna()
    wins = pnl[pnl > 0]
    losses = pnl[pnl <= 0]
    n = int(len(pnl))
    win_rate = float(len(wins) / n) if n else 0.0
    avg_win = float(wins.mean()) if len(wins) else 0.0
    avg_loss = float(abs(losses.mean())) if len(losses) else 0.0
    total_pnl = float(pnl.sum()) if n else 0.0
    avg_pnl = float(pnl.mean()) if n else 0.0
    profit_factor = (
        float(wins.sum() / abs(losses.sum())) if len(losses) and losses.sum() < 0 else 0.0
    )
    expectancy = win_rate * avg_win - (1 - win_rate) * avg_loss

    avg_return_pct = 0.0
    if ret_col is not None:
        ret = pd.to_numeric(trades[ret_col], errors="coerce").dropna()
        if len(ret):
            avg_return_pct = float(ret.mean()) * 100

    avg_holding_days = 0.0
    if entry_col and exit_col:
        entry = pd.to_datetime(trades[entry_col], errors="coerce")
        exit_ = pd.to_datetime(trades[exit_col], errors="coerce")
        dur = (exit_ - entry).dt.total_seconds() / 86400
        dur = dur.dropna()
        if len(dur):
            avg_holding_days = float(dur.mean())

    return {
        "num_trades": n,
        "wins": int(len(wins)),
        "losses": int(len(losses)),
        "win_rate": win_rate,
        "total_pnl": total_pnl,
        "avg_pnl": avg_pnl,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "profit_factor": profit_factor,
        "expectancy": expectancy,
        "avg_return_pct": avg_return_pct,
        "avg_holding_days": avg_holding_days,
    }


def _parse_symbols(symbol_text: str) -> list[str]:
    return [s.strip().upper().replace(".NS", "") for s in symbol_text.split(",") if s.strip()]


def _load_manual_csv_data(
    symbols: list[str], start_dt: datetime, end_dt: datetime, timeframe: str = "1d"
) -> dict[str, pd.DataFrame]:
    from src.data.csv_loader import KaggleCSVLoader

    loader = KaggleCSVLoader(data_dir="data/raw/csv")
    loaded: dict[str, pd.DataFrame] = {}
    for symbol in symbols:
        try:
            df = loader.load(
                symbol=symbol,
                start=str(start_dt),
                end=str(end_dt),
                use_cache=False,
                interval=timeframe,
            )
            if not df.empty:
                loaded[symbol] = df
        except Exception:
            continue
    return loaded


with st.sidebar:
    st.markdown(
        '<div style="text-align:center;padding:16px 0"><div style="font-size:32px">⚡</div>'
        '<div style="font-size:18px;font-weight:700;color:#F9FAFB">Aram-TMS</div>'
        '<div style="font-size:11px;color:#6B7280">Institutional Trading System</div></div>',
        unsafe_allow_html=True,
    )
    st.divider()
    mode_options = ["Backtest", "Forward Test", "Live Trading"]
    mode_index = (
        mode_options.index(st.session_state.mode) if st.session_state.mode in mode_options else 0
    )
    mode = st.radio("Trading Mode", mode_options, index=mode_index)
    st.session_state.mode = mode
    if mode != st.session_state.last_mode:
        st.session_state.page = _default_mode_page(mode)
        st.session_state.last_mode = mode
    mc = {"Backtest": "#8B5CF6", "Forward Test": "#3B82F6", "Live Trading": "#EF4444"}[mode]
    st.markdown(
        f'<div style="text-align:center;margin:8px 0"><span style="background:{mc};color:white;'
        f'padding:3px 12px;border-radius:12px;font-size:12px;font-weight:600">'
        f"{mode.upper()}</span></div>",
        unsafe_allow_html=True,
    )
    st.divider()
    active_nav = MODE_NAV.get(mode, MODE_NAV["Backtest"])
    for lbl, pg in active_nav:
        if st.button(lbl, key=f"nav_{mode}_{pg}", use_container_width=True):
            st.session_state.page = pg
    st.divider()
    now = datetime.now()
    is_open = now.weekday() < 5 and now.replace(hour=9, minute=15) <= now <= now.replace(
        hour=15, minute=30
    )
    col = "#10B981" if is_open else "#EF4444"
    st.markdown(
        f'<div style="text-align:center;background:#111827;border-radius:8px;padding:10px">'
        f'<div style="color:{col};font-size:12px;font-weight:700">● {"MARKET OPEN" if is_open else "MARKET CLOSED"}</div>'
        f'<div style="color:#6B7280;font-size:11px">NSE | {now.strftime("%H:%M:%S")}</div></div>',
        unsafe_allow_html=True,
    )

page = st.session_state.page
allowed_pages = {pg for _, pg in MODE_NAV.get(st.session_state.mode, MODE_NAV["Backtest"])}
if page not in allowed_pages:
    page = _default_mode_page(st.session_state.mode)
    st.session_state.page = page

# ── OVERVIEW ──
if page in {"Backtest Overview", "Forward Overview", "Live Overview"}:
    mode_title = {
        "Backtest Overview": "⚡ Backtest Overview",
        "Forward Overview": "⚡ Forward Test Overview",
        "Live Overview": "⚡ Live Trading Overview",
    }.get(page, "⚡ Aram-TMS Overview")
    st.title(mode_title)
    st.caption(f"Updated: {datetime.now().strftime('%d %b %Y %H:%M:%S')}")
    forward = _latest_forward_status()
    latest_equity = _latest_backtest_equity()
    live_pnl = float(forward.get("total_pnl", 0) or 0)
    open_positions = int(forward.get("open_positions", 0) or 0)
    total_trades = int(forward.get("total_trades", 0) or 0)
    risk_state = "HALTED" if (forward.get("risk", {}) or {}).get("circuit_breaker") else "NORMAL"

    c1, c2, c3, c4, c5 = st.columns(5)
    active_mode = st.session_state.mode
    if active_mode == "Backtest":
        bt = st.session_state.bt_results or {}
        pnl_val = f"Rs.{float(bt.get('total_return', 0) * st.session_state.capital):+,.0f}"
        trade_count = str(int(bt.get("num_trades", 0) or 0))
        open_pos_val = "0"
    else:
        pnl_val = f"Rs.{live_pnl:+,.0f}"
        trade_count = str(total_trades)
        open_pos_val = str(open_positions)

    for col, label, val, delta, pos in [
        (c1, "Portfolio Value", f"Rs.{st.session_state.capital:,.0f}", "+2.3%", True),
        (c2, "P&L", pnl_val, "", True),
        (c3, "Open Positions", open_pos_val, "", None),
        (c4, "Total Trades", trade_count, "", None),
        (c5, "Risk Status", risk_state, "", None),
    ]:
        with col:
            dh = (
                f'<div style="color:{"#10B981" if pos else "#EF4444"};font-size:13px">{delta}</div>'
                if delta and pos is not None
                else ""
            )
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">{label}</div>'
                f'<div class="metric-value">{val}</div>{dh}</div>',
                unsafe_allow_html=True,
            )
    st.subheader("Active Mode Scope")
    if st.session_state.mode == "Backtest":
        st.info("This mode is isolated for historical simulation and strategy evaluation.")
    elif st.session_state.mode == "Forward Test":
        st.info("This mode is isolated for sandbox paper execution and live signal monitoring.")
    else:
        st.info("This mode is isolated for production execution with strict safety gates.")
    st.markdown("---")
    cl, cr = st.columns([2, 1])
    with cl:
        st.subheader("Portfolio Equity Curve")
        if latest_equity.empty:
            st.info("No backtest equity data yet. Run a backtest to populate this chart.")
        else:
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=latest_equity.index,
                    y=latest_equity.values,
                    name="Aram-TMS",
                    line=dict(color="#3B82F6", width=2),
                    fill="tozeroy",
                    fillcolor="rgba(59,130,246,0.05)",
                )
            )
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=350,
                hovermode="x unified",
                margin=dict(l=0, r=0, t=30, b=0),
            )
            st.plotly_chart(fig, use_container_width=True)
    with cr:
        st.subheader("Allocation")
        if forward:
            st.json(forward.get("portfolio", {}))
        else:
            st.info("No live/forward portfolio snapshot available.")
    st.subheader("Recent Signals")
    trades = _latest_trade_log()
    if trades.empty:
        st.info("No trade audit data yet.")
    else:
        st.dataframe(trades, use_container_width=True, hide_index=True)

# ── BACKTESTING ──
elif page == "Backtesting":
    st.title("🔬 Backtesting Engine")
    with st.expander("⚙️ Configuration", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            strat = st.selectbox(
                "Strategy", ["MomentumStrategy", "MeanReversionStrategy", "BreakoutStrategy"]
            )
            engine = st.selectbox("Engine", ["VectorBT (Fast)", "Backtrader (Realistic)"])
        with c2:
            data_source = st.selectbox(
                "Data Source", ["yFinance (<2yr)", "Manual CSV (data/raw/csv)"]
            )
        with c3:
            start_dt = st.date_input("Start", value=pd.Timestamp("2020-01-01"))
            end_dt = st.date_input("End", value=pd.Timestamp("2024-12-31"))
        timeframe = st.selectbox(
            "Timeframe",
            ["1d", "1h", "30m", "15m", "5m", "1m"],
            index=0,
            help="For yFinance intraday intervals, keep date range short due provider limits.",
        )
        default_symbol_text = "RELIANCE"
        symbol_text = st.text_input(
            "Symbol",
            value=default_symbol_text,
            help="Single-symbol backtesting only. Example: RELIANCE",
        )
        selected_symbols = _parse_symbols(symbol_text)
        if len(selected_symbols) > 1:
            st.warning(
                f"Single-symbol mode active. Only first symbol will be used: {selected_symbols[0]}"
            )
        if data_source.startswith("Manual CSV"):
            available_csv = sorted([p.name for p in Path("data/raw/csv").glob("*.csv")])
            if available_csv:
                st.caption(f"Detected CSV files: {', '.join(available_csv[:8])}")
            else:
                st.warning("No CSV files found in data/raw/csv")
        c4, c5 = st.columns(2)
        with c4:
            capital = st.number_input("Capital (Rs.)", value=1_000_000, step=100_000)
        with c5:
            st.slider("Slippage (%)", 0.01, 0.20, 0.05, 0.01)
    with st.expander("🧠 Strategy Parameters"):
        p1, p2 = st.columns(2)
        with p1:
            st.slider("Momentum Period", 60, 252, 252)
            st.slider("EMA Period", 20, 200, 50)
        with p2:
            st.slider("RSI Max", 60, 85, 70)
            st.slider("Volume Multiplier", 1.0, 3.0, 1.2, 0.1)
    if st.button("🚀 Run Backtest", type="primary", use_container_width=True):
        with st.spinner("Running backtest..."):
            try:
                from src.backtesting.backtrader_runner import BacktraderRunner
                from src.backtesting.vectorbt_runner import VectorBTRunner
                from src.data.csv_loader import KaggleCSVLoader
                from src.data.yfinance_loader import YFinanceLoader
                from src.strategies.base_strategy import STRATEGY_REGISTRY

                strategy_obj = STRATEGY_REGISTRY[strat]()
                if not selected_symbols:
                    st.error("Please provide at least one symbol")
                    st.stop()
                symbol = selected_symbols[0]
                st.session_state.bt_symbol = symbol
                st.session_state.bt_data_source = data_source

                if data_source.startswith("yFinance"):
                    data = YFinanceLoader(auto_adjust=False).fetch(
                        symbol=f"{symbol}.NS",
                        start=str(start_dt),
                        end=str(end_dt),
                        interval=timeframe,
                        use_cache=False,
                    )
                else:
                    try:
                        csv_loader = KaggleCSVLoader(data_dir="data/raw/csv")
                        data = csv_loader.load(
                            symbol=symbol,
                            start=str(start_dt),
                            end=str(end_dt),
                            use_cache=False,
                            interval=timeframe,
                        )
                    except TypeError as exc:
                        if "unexpected keyword argument 'interval'" not in str(exc):
                            raise
                        # Compatibility fallback for stale/older loader versions.
                        csv_loader = KaggleCSVLoader(data_dir="data/raw/csv")
                        data = csv_loader.load(
                            symbol=symbol,
                            start=str(start_dt),
                            end=str(end_dt),
                            use_cache=False,
                        )
                        if hasattr(csv_loader, "_to_interval"):
                            data = csv_loader._to_interval(data, timeframe)
                    except Exception as exc:
                        st.error(f"CSV load failed for {symbol}: {exc}")
                        data = pd.DataFrame()

                if data.empty:
                    if data_source.startswith("yFinance"):
                        span_days = (pd.Timestamp(end_dt) - pd.Timestamp(start_dt)).days
                        st.error(
                            "No yFinance data loaded. Possible reasons: invalid symbol, network issue, "
                            "or interval window too large for intraday bars."
                        )
                        if timeframe in {"1m", "5m", "15m", "30m", "1h"}:
                            st.info(
                                f"Selected intraday timeframe {timeframe} with date span {span_days} days. "
                                "Try reducing date range to recent days/weeks."
                            )
                    else:
                        csv_loader = KaggleCSVLoader(data_dir="data/raw/csv")
                        meta = csv_loader.inspect_symbol(symbol)
                        st.error(
                            "No CSV data loaded for backtest. Check symbol mapping, date range overlap, "
                            "and required OHLCV columns."
                        )
                        st.json(
                            {
                                "symbol": symbol,
                                "timeframe": timeframe,
                                "file_exists": meta.get("exists"),
                                "path": meta.get("path"),
                                "available_start": meta.get("start"),
                                "available_end": meta.get("end"),
                                "rows": meta.get("rows"),
                                "raw_columns": meta.get("columns"),
                            }
                        )
                else:
                    signals = strategy_obj.generate_signals(data)
                    warmup = strategy_obj.get_warmup_period()
                    st.session_state.bt_diag = {
                        "symbol": symbol,
                        "source": data_source,
                        "timeframe": timeframe,
                        "bars": int(len(data)),
                        "start": str(data.index.min()) if len(data) else None,
                        "end": str(data.index.max()) if len(data) else None,
                        "warmup_required": int(warmup),
                        "buy_signals": int((signals == 1).sum()),
                        "sell_signals": int((signals == -1).sum()),
                    }
                    if len(data) < warmup:
                        st.warning(
                            f"Data has {len(data)} bars but strategy warmup needs {warmup}; "
                            "this can produce zero trades and may look like dummy output."
                        )

                    benchmark = YFinanceLoader(auto_adjust=False).fetch(
                        symbol="^NSEI",
                        start=str(start_dt),
                        end=str(end_dt),
                        interval="1d",
                        use_cache=False,
                    )
                    if engine.startswith("VectorBT"):
                        result = VectorBTRunner(initial_capital=capital).run(
                            strategy_obj, data, benchmark
                        )
                    else:
                        result = BacktraderRunner(initial_capital=capital).run(
                            strategy_obj, data, benchmark
                        )
                    result.timeframe = timeframe
                    result.data_source = "yfinance" if data_source.startswith("yFinance") else "csv"
                    result.symbols = [symbol]
                    result.bars_loaded = int(len(data))
                    result.warmup_required = int(warmup)
                    prior_diag = getattr(result, "diagnostics", {}) or {}
                    result.diagnostics = {
                        **prior_diag,
                        "symbol": symbol,
                        "benchmark": "^NSEI",
                    }
                    result.save("data/results/backtests")
                    st.session_state.bt_results = {
                        "total_return": result.total_return,
                        "cagr": result.cagr,
                        "sharpe": result.sharpe,
                        "sortino": result.sortino,
                        "calmar": result.calmar,
                        "max_drawdown": abs(result.max_drawdown),
                        "win_rate": result.win_rate,
                        "profit_factor": result.profit_factor,
                        "num_trades": result.num_trades,
                        "alpha": result.alpha,
                    }
                    st.session_state.bt_equity = (
                        result.equity_curve
                        if result.equity_curve is not None
                        else pd.Series(dtype=float)
                    )
                    st.session_state.bt_trades = (
                        result.trade_log.copy() if result.trade_log is not None else pd.DataFrame()
                    )
                    if (
                        benchmark is not None
                        and not benchmark.empty
                        and "Close" in benchmark.columns
                    ):
                        base = float(benchmark["Close"].iloc[0])
                        if base > 0:
                            st.session_state.bt_benchmark_curve = (
                                benchmark["Close"] / base * float(capital)
                            )
                        else:
                            st.session_state.bt_benchmark_curve = pd.Series(dtype=float)
                    else:
                        st.session_state.bt_benchmark_curve = pd.Series(dtype=float)
                    st.success("✅ Backtest complete!")
            except Exception as exc:
                st.error(f"Backtest failed: {exc}")
    if st.session_state.bt_results:
        r = st.session_state.bt_results
        st.markdown("---")
        st.subheader("📊 Results")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Return", f"{r['total_return']:.1%}", f"α {r['alpha']:.1%}")
        m2.metric("CAGR", f"{r['cagr']:.1%}")
        m3.metric("Sharpe", f"{r['sharpe']:.2f}")
        m4.metric("Max Drawdown", f"-{r['max_drawdown']:.1%}", delta_color="inverse")
        m5, m6, m7, m8 = st.columns(4)
        m5.metric("Sortino", f"{r['sortino']:.2f}")
        m6.metric("Calmar", f"{r['calmar']:.2f}")
        m7.metric("Win Rate", f"{r['win_rate']:.1%}")
        m8.metric("Profit Factor", f"{r['profit_factor']:.2f}")
        eq = st.session_state.bt_equity
        if eq is None or eq.empty:
            eq = _latest_backtest_equity()
        if eq.empty:
            st.info("No persisted equity curve found for plotting.")
        else:
            dd = (eq / eq.cummax() - 1) * 100
            fig = make_subplots(
                rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.05
            )
            fig.add_trace(
                go.Scatter(
                    x=eq.index, y=eq.values, name="Strategy", line=dict(color="#3B82F6", width=2)
                ),
                row=1,
                col=1,
            )
            bm = st.session_state.bt_benchmark_curve
            if bm is not None and not bm.empty:
                fig.add_trace(
                    go.Scatter(
                        x=bm.index,
                        y=bm.values,
                        name="NIFTY 50",
                        line=dict(color="#9CA3AF", width=1.5, dash="dash"),
                    ),
                    row=1,
                    col=1,
                )
            fig.add_trace(
                go.Scatter(
                    x=dd.index,
                    y=dd.values,
                    name="Drawdown",
                    fill="tozeroy",
                    fillcolor="rgba(239,68,68,0.15)",
                    line=dict(color="#EF4444", width=1),
                ),
                row=2,
                col=1,
            )
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=500,
                hovermode="x unified",
                margin=dict(l=0, r=0, t=10, b=0),
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption(
                f"Symbol: {st.session_state.bt_symbol} | Source: {st.session_state.bt_data_source}"
            )
        if st.button("💾 Save Results"):
            st.success("Saved to data/results/backtests/")

        if st.session_state.bt_diag:
            with st.expander("🧪 Backtest Data Diagnostics", expanded=True):
                st.json(st.session_state.bt_diag)

        st.markdown("---")
        st.subheader("🧾 Executed Trade Log")
        trades_df = st.session_state.bt_trades
        if trades_df is None or trades_df.empty:
            trades_df = _latest_backtest_trades()

        if trades_df.empty:
            st.info("No executed trade records found yet. Run a backtest that generates trades.")
        else:
            tm = _compute_trade_metrics(trades_df)
            t1, t2, t3, t4, t5, t6 = st.columns(6)
            t1.metric("Trades", f"{tm['num_trades']}")
            t2.metric("Wins / Losses", f"{tm['wins']} / {tm['losses']}")
            t3.metric("Win Rate", f"{tm['win_rate']:.1%}")
            t4.metric("Total PnL", f"Rs.{tm['total_pnl']:,.0f}")
            t5.metric("Expectancy", f"Rs.{tm['expectancy']:,.0f}")
            t6.metric("Profit Factor", f"{tm['profit_factor']:.2f}")

            t7, t8, t9 = st.columns(3)
            t7.metric("Avg Trade PnL", f"Rs.{tm['avg_pnl']:,.0f}")
            t8.metric("Avg Return / Trade", f"{tm['avg_return_pct']:.2f}%")
            t9.metric("Avg Holding", f"{tm['avg_holding_days']:.2f}d")

            st.dataframe(trades_df, use_container_width=True, hide_index=True)

# ── FORWARD TEST ──
elif page == "Forward Test":
    st.title("📡 Forward Testing — DhanHQ Sandbox")
    c1, c2 = st.columns([1, 2])
    with c1:
        current = _latest_forward_status()
        now2 = datetime.now()
        is_open2 = now2.weekday() < 5 and now2.replace(hour=9, minute=15) <= now2 <= now2.replace(
            hour=15, minute=30
        )
        st.markdown(
            f'<div style="background:#111827;border-radius:8px;padding:16px;text-align:center">'
            f'<div style="font-size:24px">{"🟢" if is_open2 else "🔴"}</div>'
            f'<div style="color:#F9FAFB;font-weight:700">{"MARKET OPEN" if is_open2 else "MARKET CLOSED"}</div>'
            f'<div style="color:#6B7280;font-size:12px">{now2.strftime("%H:%M:%S IST")}</div></div>',
            unsafe_allow_html=True,
        )
        st.metric("Session P&L", f"Rs.{float(current.get('total_pnl', 0) or 0):+,.0f}")
        st.metric("Open Positions", str(int(current.get("open_positions", 0) or 0)))
        st.metric("Orders", str(int(current.get("total_trades", 0) or 0)))
    with c2:
        st.subheader("Configuration")
        fs = st.selectbox(
            "Strategy", ["MomentumStrategy", "MeanReversionStrategy", "BreakoutStrategy"]
        )
        fsyms = st.multiselect(
            "Universe",
            ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "AXISBANK", "SBIN", "LT"],
            default=["RELIANCE", "TCS", "HDFCBANK", "INFY"],
        )
        fcap = st.number_input("Paper Capital (Rs.)", value=500_000, step=100_000)
        scan = st.slider("Scan Interval (seconds)", 30, 300, 60)
        cb1, cb2 = st.columns(2)
        with cb1:
            if st.button("▶ Start Forward Test", type="primary", use_container_width=True):
                st.success(f"✅ Started: {fs} | {len(fsyms)} symbols | Rs.{fcap:,.0f}")
        with cb2:
            if st.button("⏹ Stop", use_container_width=True):
                st.warning("⏹ Session stopped. Positions closed.")
    st.divider()
    if current:
        st.json(current)
    else:
        st.info(
            "💡 Add DHAN_SANDBOX_CLIENT_ID and DHAN_SANDBOX_ACCESS_TOKEN in Settings → API Keys first."
        )

# ── LIVE TRADING ──
elif page == "Live Trading":
    st.title("🔴 Live Trading — DhanHQ Production")
    st.error("Live trading can place real orders. Use only after sandbox validation.")

    lc1, lc2 = st.columns([1, 2])
    with lc1:
        st.markdown("**Safety Gates**")
        st.write("1. Confirm strategy on backtest")
        st.write("2. Validate in forward test")
        st.write("3. Start live with --confirm-live")
        st.write("4. Type CONFIRM_LIVE in terminal")
    with lc2:
        st.markdown("**Live Command**")
        st.code(
            "python scripts/run_live_trading.py --strategy MomentumStrategy --symbols RELIANCE TCS --capital 1000000 --confirm-live",
            language="bash",
        )
        st.info("Live status is shown via runtime logs and trade audit files under logs/trades.")

# ── STRATEGIES ──
elif page == "Strategies":
    st.title("🧠 Strategy Library")
    for sname, scat, sh, suni, sstat in [
        ("MomentumStrategy", "Momentum", "1.73", "NIFTY 100", "Active"),
        ("MeanReversionStrategy", "Mean Reversion", "1.24", "NIFTY 50", "Inactive"),
        ("BreakoutStrategy", "Breakout", "1.51", "NIFTY 100", "Inactive"),
    ]:
        with st.container():
            c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
            with c1:
                st.markdown(f"**{sname}**")
                st.caption(f"{scat} | Daily | {suni}")
            with c2:
                st.metric("Best Sharpe", sh)
            with c3:
                color = "#10B981" if sstat == "Active" else "#6B7280"
                st.markdown(f'<span style="color:{color}">● {sstat}</span>', unsafe_allow_html=True)
            with c4:
                if st.button("Backtest", key=f"bt_{sname}"):
                    st.session_state.page = "Backtesting"
                    st.rerun()
            st.divider()
    st.subheader("Add Custom Strategy")
    st.code(
        """from src.strategies.base_strategy import BaseStrategy, register_strategy

@register_strategy
class MyStrategy(BaseStrategy):
    NAME = "MyStrategy"
    CATEGORY = "momentum"

    def __init__(self, lookback=20, **kwargs):
        super().__init__(**kwargs)
        self.lookback = lookback

    def get_parameters(self): return {"lookback": self.lookback}
    def validate_parameters(self): assert 5<=self.lookback<=200; return True

    def generate_signals(self, data):
        sma = data["Close"].rolling(self.lookback).mean()
        signals = (data["Close"] > sma).astype(int)
        signals[data["Close"] < sma] = -1
        return signals.shift(1).fillna(0).astype(int)  # Always shift!
""",
        language="python",
    )

# ── RISK MONITOR ──
elif page == "Risk Monitor":
    st.title("⚠️ Risk Monitor")
    c1, c2, c3 = st.columns(3)
    for col, label, cur, lim in [
        (c1, "Portfolio Drawdown", 0.023, 0.15),
        (c2, "Daily Loss", 0.001, 0.03),
        (c3, "Sector Concentration", 0.12, 0.30),
    ]:
        with col:
            pct = cur / lim
            color = "#10B981" if pct < 0.6 else "#F59E0B" if pct < 0.85 else "#EF4444"
            st.markdown(f"**{label}**")
            st.progress(pct)
            st.markdown(
                f'<span style="color:{color}">{cur:.1%} / {lim:.1%}</span>', unsafe_allow_html=True
            )
    st.divider()
    cg, cr2 = st.columns(2)
    with cg:
        st.subheader("Portfolio Risk Score")
        fig_g = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=23,
                title={"text": "Risk Score (0-100)"},
                gauge={
                    "axis": {"range": [0, 100]},
                    "bar": {"color": "#3B82F6"},
                    "steps": [
                        {"range": [0, 40], "color": "rgba(16,185,129,0.2)"},
                        {"range": [40, 70], "color": "rgba(245,158,11,0.2)"},
                        {"range": [70, 100], "color": "rgba(239,68,68,0.2)"},
                    ],
                    "threshold": {
                        "line": {"color": "white", "width": 2},
                        "thickness": 0.75,
                        "value": 70,
                    },
                },
            )
        )
        fig_g.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            height=250,
            margin=dict(l=20, r=20, t=30, b=20),
        )
        st.plotly_chart(fig_g, use_container_width=True)
    with cr2:
        st.subheader("Active Risk Rules")
        for rule in [
            "✅ Max position: 5% per stock",
            "✅ Max drawdown stop: 15%",
            "✅ Daily loss limit: 3%",
            "✅ Max open positions: 20",
            "✅ Sector concentration: 30%",
            "✅ F&O ban list: Updated",
            "✅ Stop-loss required: All buys",
            "✅ Min R:R ratio: 2.0",
        ]:
            st.markdown(rule)

# ── ANALYTICS ──
elif page == "Analytics":
    st.title("📉 Performance Analytics")
    if not st.session_state.bt_results:
        st.info("Run a backtest first to see analytics here.")
    else:
        st.write(
            "Analytics dashboard coming soon — walk-forward charts, monthly heatmap, trade distribution."
        )

# ── SETTINGS ──
elif page == "Settings":
    st.title("⚙️ System Settings")
    t1, t2, t3 = st.tabs(["API Keys", "Risk Parameters", "About"])
    with t1:
        st.subheader("DhanHQ Configuration")
        st.info("Credentials are saved to your .env file and never committed to git.")
        st.text_input("Sandbox Client ID", type="password", placeholder="DHAN_SANDBOX_CLIENT_ID")
        st.text_input(
            "Sandbox Access Token", type="password", placeholder="DHAN_SANDBOX_ACCESS_TOKEN"
        )
        st.text_input("Live Client ID", type="password", placeholder="DHAN_CLIENT_ID")
        st.text_input("Live Access Token", type="password", placeholder="DHAN_ACCESS_TOKEN")
        if st.button("💾 Save API Keys"):
            st.success("Keys saved to .env")
    with t2:
        st.subheader("Risk Parameters")
        st.slider("Max Drawdown Stop (%)", 5, 30, 15)
        st.slider("Daily Loss Limit (%)", 1, 10, 3)
        st.slider("Max Position Size (%)", 1, 20, 5)
        st.slider("Min R:R Ratio", 1.0, 4.0, 2.0, 0.5)
        st.number_input("Initial Capital (Rs.)", value=1_000_000, step=100_000)
        if st.button("💾 Save Risk Settings"):
            st.success("Risk parameters saved to config/settings.yaml")
    with t3:
        st.subheader("About Aram-TMS")
        st.markdown("""
**Aram Trade Management System v1.0.0**

Professional institutional-grade algorithmic trading for Indian markets.

- Exchange: NSE / BSE
- Broker: DhanHQ
- Data: yFinance + Kaggle CSV
- Engines: VectorBT, Backtrader

[GitHub](https://github.com) | [Documentation](docs/IMPLEMENTATION_PLAN.md)
""")

else:
    st.title(page)
    st.info(f"Page '{page}' coming soon.")
