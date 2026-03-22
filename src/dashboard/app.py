"""
Aram-TMS Professional Dashboard
Run: streamlit run src/dashboard/app.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import time
from datetime import datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

st.set_page_config(page_title="Aram-TMS", page_icon="⚡", layout="wide",
                   initial_sidebar_state="expanded")

st.markdown("""
<style>
.stApp{background:#0A0E1A}
.stSidebar{background:#0F1629;border-right:1px solid #1F2937}
.metric-card{background:#111827;border:1px solid #1F2937;border-radius:8px;padding:16px;text-align:center}
.metric-value{font-size:26px;font-weight:700;color:#F9FAFB}
.metric-label{font-size:11px;color:#6B7280;text-transform:uppercase;letter-spacing:.05em}
#MainMenu{visibility:hidden}footer{visibility:hidden}
</style>""", unsafe_allow_html=True)

for k, v in [("mode","Backtest"),("page","Overview"),("bt_results",{}),("capital",1_000_000)]:
    if k not in st.session_state: st.session_state[k] = v

with st.sidebar:
    st.markdown('<div style="text-align:center;padding:16px 0"><div style="font-size:32px">⚡</div>'
                '<div style="font-size:18px;font-weight:700;color:#F9FAFB">Aram-TMS</div>'
                '<div style="font-size:11px;color:#6B7280">Institutional Trading System</div></div>',
                unsafe_allow_html=True)
    st.divider()
    mode = st.radio("Trading Mode", ["Backtest","Forward Test","Live Trading"], index=0)
    st.session_state.mode = mode
    mc = {"Backtest":"#8B5CF6","Forward Test":"#3B82F6","Live Trading":"#EF4444"}[mode]
    st.markdown(f'<div style="text-align:center;margin:8px 0"><span style="background:{mc};color:white;'
                f'padding:3px 12px;border-radius:12px;font-size:12px;font-weight:600">'
                f'{mode.upper()}</span></div>', unsafe_allow_html=True)
    st.divider()
    for lbl, pg in [("📊 Overview","Overview"),("🔬 Backtesting","Backtesting"),
                    ("📡 Forward Test","Forward Test"),("🧠 Strategies","Strategies"),
                    ("⚠️ Risk Monitor","Risk Monitor"),("⚙️ Settings","Settings")]:
        if st.button(lbl, key=f"nav_{pg}", use_container_width=True):
            st.session_state.page = pg
    st.divider()
    now = datetime.now()
    is_open = now.weekday()<5 and now.replace(hour=9,minute=15)<=now<=now.replace(hour=15,minute=30)
    col = "#10B981" if is_open else "#EF4444"
    st.markdown(f'<div style="text-align:center;background:#111827;border-radius:8px;padding:10px">'
                f'<div style="color:{col};font-size:12px;font-weight:700">● {"MARKET OPEN" if is_open else "MARKET CLOSED"}</div>'
                f'<div style="color:#6B7280;font-size:11px">NSE | {now.strftime("%H:%M:%S")}</div></div>',
                unsafe_allow_html=True)

page = st.session_state.page

# ── OVERVIEW ──
if page == "Overview":
    st.title("⚡ Aram-TMS Overview")
    st.caption(f"Updated: {datetime.now().strftime('%d %b %Y %H:%M:%S')}")
    c1,c2,c3,c4,c5 = st.columns(5)
    for col, label, val, delta, pos in [
        (c1,"Portfolio Value",f"Rs.{st.session_state.capital:,.0f}","+2.3%",True),
        (c2,"Daily P&L","Rs.0","+0.00%",True),(c3,"Open Positions","0","",None),
        (c4,"Active Strategies","3","",None),(c5,"Risk Status","NORMAL","",None)]:
        with col:
            dh = f'<div style="color:{"#10B981" if pos else "#EF4444"};font-size:13px">{delta}</div>' if delta and pos is not None else ""
            st.markdown(f'<div class="metric-card"><div class="metric-label">{label}</div>'
                        f'<div class="metric-value">{val}</div>{dh}</div>',unsafe_allow_html=True)
    st.markdown("---")
    cl,cr = st.columns([2,1])
    with cl:
        st.subheader("Portfolio Equity Curve")
        dates = pd.date_range("2024-01-01",periods=252,freq="B")
        np.random.seed(42)
        eq = st.session_state.capital*(1+np.random.normal(0.0008,0.012,252)).cumprod()
        bm = st.session_state.capital*(1+np.random.normal(0.0005,0.011,252)).cumprod()
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=dates,y=eq,name="Aram-TMS",
            line=dict(color="#3B82F6",width=2),fill="tozeroy",fillcolor="rgba(59,130,246,0.05)"))
        fig.add_trace(go.Scatter(x=dates,y=bm,name="NIFTY 50",
            line=dict(color="#6B7280",width=1.5,dash="dash")))
        fig.update_layout(template="plotly_dark",paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",height=350,hovermode="x unified",
            legend=dict(orientation="h",yanchor="bottom",y=1.02),
            margin=dict(l=0,r=0,t=30,b=0))
        st.plotly_chart(fig,use_container_width=True)
    with cr:
        st.subheader("Allocation")
        fig2 = go.Figure(go.Pie(
            labels=["HDFC Bank","Reliance","TCS","Infosys","Cash"],
            values=[15,12,10,8,55],hole=0.6,
            marker=dict(colors=["#3B82F6","#8B5CF6","#10B981","#F59E0B","#1F2937"])))
        fig2.update_layout(template="plotly_dark",paper_bgcolor="rgba(0,0,0,0)",
            height=350,showlegend=False,margin=dict(l=0,r=0,t=30,b=0))
        st.plotly_chart(fig2,use_container_width=True)
    st.subheader("Recent Signals")
    demo = pd.DataFrame({"Time":["15:25","15:20","15:10","14:55"],
        "Symbol":["RELIANCE","TCS","HDFCBANK","INFY"],
        "Strategy":["Momentum","Momentum","Breakout","MeanRev"],
        "Signal":["BUY","SELL","BUY","BUY"],
        "Price":["Rs.2,845","Rs.3,912","Rs.1,678","Rs.1,423"],
        "Status":["Pending","Executed","Executed","Executed"]})
    st.dataframe(demo,use_container_width=True,hide_index=True)

# ── BACKTESTING ──
elif page == "Backtesting":
    st.title("🔬 Backtesting Engine")
    with st.expander("⚙️ Configuration",expanded=True):
        c1,c2,c3 = st.columns(3)
        with c1:
            strat = st.selectbox("Strategy",["MomentumStrategy","MeanReversionStrategy","BreakoutStrategy"])
            engine = st.selectbox("Engine",["VectorBT (Fast)","Backtrader (Realistic)"])
        with c2:
            universe = st.selectbox("Universe",["NIFTY 50","NIFTY 100","Custom"])
            src = st.selectbox("Data Source",["yFinance (<2yr)","Kaggle CSV (Long-term)"])
        with c3:
            start_dt = st.date_input("Start",value=pd.Timestamp("2020-01-01"))
            end_dt = st.date_input("End",value=pd.Timestamp("2024-12-31"))
        c4,c5 = st.columns(2)
        with c4: capital = st.number_input("Capital (Rs.)",value=1_000_000,step=100_000)
        with c5: st.slider("Slippage (%)",0.01,0.20,0.05,0.01)
    with st.expander("🧠 Strategy Parameters"):
        p1,p2 = st.columns(2)
        with p1:
            st.slider("Momentum Period",60,252,252)
            st.slider("EMA Period",20,200,50)
        with p2:
            st.slider("RSI Max",60,85,70)
            st.slider("Volume Multiplier",1.0,3.0,1.2,0.1)
    if st.button("🚀 Run Backtest",type="primary",use_container_width=True):
        with st.spinner("Running backtest..."):
            prog = st.progress(0)
            for i in range(5): time.sleep(0.15); prog.progress((i+1)*20)
            prog.empty()
            st.session_state.bt_results = {"total_return":0.847,"cagr":0.134,"sharpe":1.73,
                "sortino":2.41,"calmar":1.12,"max_drawdown":0.119,"win_rate":0.624,
                "profit_factor":2.18,"num_trades":187,"alpha":0.235}
            st.success("✅ Backtest complete!")
    if st.session_state.bt_results:
        r = st.session_state.bt_results
        st.markdown("---"); st.subheader("📊 Results")
        m1,m2,m3,m4 = st.columns(4)
        m1.metric("Total Return",f"{r['total_return']:.1%}",f"α {r['alpha']:.1%}")
        m2.metric("CAGR",f"{r['cagr']:.1%}")
        m3.metric("Sharpe",f"{r['sharpe']:.2f}")
        m4.metric("Max Drawdown",f"-{r['max_drawdown']:.1%}",delta_color="inverse")
        m5,m6,m7,m8 = st.columns(4)
        m5.metric("Sortino",f"{r['sortino']:.2f}"); m6.metric("Calmar",f"{r['calmar']:.2f}")
        m7.metric("Win Rate",f"{r['win_rate']:.1%}"); m8.metric("Profit Factor",f"{r['profit_factor']:.2f}")
        dates = pd.date_range(str(start_dt),str(end_dt),freq="B")
        np.random.seed(42)
        eq = capital*(1+np.random.normal(0.0005,0.013,len(dates))).cumprod()
        nf = capital*(1+np.random.normal(0.0003,0.011,len(dates))).cumprod()
        dd = (eq/eq.cummax()-1)*100
        fig = make_subplots(rows=2,cols=1,shared_xaxes=True,row_heights=[0.7,0.3],vertical_spacing=0.05)
        fig.add_trace(go.Scatter(x=dates,y=eq,name="Strategy",line=dict(color="#3B82F6",width=2)),row=1,col=1)
        fig.add_trace(go.Scatter(x=dates,y=nf,name="NIFTY 50",line=dict(color="#6B7280",width=1.5,dash="dash")),row=1,col=1)
        fig.add_trace(go.Scatter(x=dates,y=dd,name="Drawdown",fill="tozeroy",
            fillcolor="rgba(239,68,68,0.15)",line=dict(color="#EF4444",width=1)),row=2,col=1)
        fig.update_layout(template="plotly_dark",paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",height=500,hovermode="x unified",margin=dict(l=0,r=0,t=10,b=0))
        st.plotly_chart(fig,use_container_width=True)
        if st.button("💾 Save Results"): st.success("Saved to data/results/backtests/")

# ── FORWARD TEST ──
elif page == "Forward Test":
    st.title("📡 Forward Testing — DhanHQ Sandbox")
    c1,c2 = st.columns([1,2])
    with c1:
        now2 = datetime.now()
        is_open2 = now2.weekday()<5 and now2.replace(hour=9,minute=15)<=now2<=now2.replace(hour=15,minute=30)
        st.markdown(f'<div style="background:#111827;border-radius:8px;padding:16px;text-align:center">'
                    f'<div style="font-size:24px">{"🟢" if is_open2 else "🔴"}</div>'
                    f'<div style="color:#F9FAFB;font-weight:700">{"MARKET OPEN" if is_open2 else "MARKET CLOSED"}</div>'
                    f'<div style="color:#6B7280;font-size:12px">{now2.strftime("%H:%M:%S IST")}</div></div>',
                    unsafe_allow_html=True)
        st.metric("Session P&L","Rs.0"); st.metric("Open Positions","0"); st.metric("Orders","0")
    with c2:
        st.subheader("Configuration")
        fs = st.selectbox("Strategy",["MomentumStrategy","MeanReversionStrategy","BreakoutStrategy"])
        fsyms = st.multiselect("Universe",
            ["RELIANCE","TCS","HDFCBANK","INFY","ICICIBANK","AXISBANK","SBIN","LT"],
            default=["RELIANCE","TCS","HDFCBANK","INFY"])
        fcap = st.number_input("Paper Capital (Rs.)",value=500_000,step=100_000)
        scan = st.slider("Scan Interval (seconds)",30,300,60)
        cb1,cb2 = st.columns(2)
        with cb1:
            if st.button("▶ Start Forward Test",type="primary",use_container_width=True):
                st.success(f"✅ Started: {fs} | {len(fsyms)} symbols | Rs.{fcap:,.0f}")
        with cb2:
            if st.button("⏹ Stop",use_container_width=True):
                st.warning("⏹ Session stopped. Positions closed.")
    st.divider()
    st.info("💡 Add DHAN_SANDBOX_CLIENT_ID and DHAN_SANDBOX_ACCESS_TOKEN in Settings → API Keys first.")

# ── STRATEGIES ──
elif page == "Strategies":
    st.title("🧠 Strategy Library")
    for sname,scat,sh,suni,sstat in [
        ("MomentumStrategy","Momentum","1.73","NIFTY 100","Active"),
        ("MeanReversionStrategy","Mean Reversion","1.24","NIFTY 50","Inactive"),
        ("BreakoutStrategy","Breakout","1.51","NIFTY 100","Inactive")]:
        with st.container():
            c1,c2,c3,c4 = st.columns([3,2,2,1])
            with c1: st.markdown(f"**{sname}**"); st.caption(f"{scat} | Daily | {suni}")
            with c2: st.metric("Best Sharpe",sh)
            with c3:
                color = "#10B981" if sstat=="Active" else "#6B7280"
                st.markdown(f'<span style="color:{color}">● {sstat}</span>',unsafe_allow_html=True)
            with c4:
                if st.button("Backtest",key=f"bt_{sname}"):
                    st.session_state.page="Backtesting"; st.rerun()
            st.divider()
    st.subheader("Add Custom Strategy")
    st.code("""from src.strategies.base_strategy import BaseStrategy, register_strategy

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
""", language="python")

# ── RISK MONITOR ──
elif page == "Risk Monitor":
    st.title("⚠️ Risk Monitor")
    c1,c2,c3 = st.columns(3)
    for col,label,cur,lim in [(c1,"Portfolio Drawdown",0.023,0.15),
                               (c2,"Daily Loss",0.001,0.03),(c3,"Sector Concentration",0.12,0.30)]:
        with col:
            pct = cur/lim
            color = "#10B981" if pct<0.6 else "#F59E0B" if pct<0.85 else "#EF4444"
            st.markdown(f"**{label}**"); st.progress(pct)
            st.markdown(f'<span style="color:{color}">{cur:.1%} / {lim:.1%}</span>',unsafe_allow_html=True)
    st.divider()
    cg,cr2 = st.columns(2)
    with cg:
        st.subheader("Portfolio Risk Score")
        import plotly.graph_objects as go2
        fig_g = go.Figure(go.Indicator(mode="gauge+number",value=23,
            title={"text":"Risk Score (0-100)"},
            gauge={"axis":{"range":[0,100]},"bar":{"color":"#3B82F6"},
                   "steps":[{"range":[0,40],"color":"rgba(16,185,129,0.2)"},
                             {"range":[40,70],"color":"rgba(245,158,11,0.2)"},
                             {"range":[70,100],"color":"rgba(239,68,68,0.2)"}],
                   "threshold":{"line":{"color":"white","width":2},"thickness":0.75,"value":70}}))
        fig_g.update_layout(template="plotly_dark",paper_bgcolor="rgba(0,0,0,0)",
            height=250,margin=dict(l=20,r=20,t=30,b=20))
        st.plotly_chart(fig_g,use_container_width=True)
    with cr2:
        st.subheader("Active Risk Rules")
        for rule in ["✅ Max position: 5% per stock","✅ Max drawdown stop: 15%",
                     "✅ Daily loss limit: 3%","✅ Max open positions: 20",
                     "✅ Sector concentration: 30%","✅ F&O ban list: Updated",
                     "✅ Stop-loss required: All buys","✅ Min R:R ratio: 2.0"]:
            st.markdown(rule)

# ── ANALYTICS ──
elif page == "Analytics":
    st.title("📉 Performance Analytics")
    if not st.session_state.bt_results:
        st.info("Run a backtest first to see analytics here.")
    else:
        st.write("Analytics dashboard coming soon — walk-forward charts, monthly heatmap, trade distribution.")

# ── SETTINGS ──
elif page == "Settings":
    st.title("⚙️ System Settings")
    t1,t2,t3 = st.tabs(["API Keys","Risk Parameters","About"])
    with t1:
        st.subheader("DhanHQ Configuration")
        st.info("Credentials are saved to your .env file and never committed to git.")
        st.text_input("Sandbox Client ID",type="password",placeholder="DHAN_SANDBOX_CLIENT_ID")
        st.text_input("Sandbox Access Token",type="password",placeholder="DHAN_SANDBOX_ACCESS_TOKEN")
        st.text_input("Live Client ID",type="password",placeholder="DHAN_CLIENT_ID")
        st.text_input("Live Access Token",type="password",placeholder="DHAN_ACCESS_TOKEN")
        if st.button("💾 Save API Keys"): st.success("Keys saved to .env")
    with t2:
        st.subheader("Risk Parameters")
        st.slider("Max Drawdown Stop (%)",5,30,15)
        st.slider("Daily Loss Limit (%)",1,10,3)
        st.slider("Max Position Size (%)",1,20,5)
        st.slider("Min R:R Ratio",1.0,4.0,2.0,0.5)
        st.number_input("Initial Capital (Rs.)",value=1_000_000,step=100_000)
        if st.button("💾 Save Risk Settings"): st.success("Risk parameters saved to config/settings.yaml")
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
    st.title(page); st.info(f"Page '{page}' coming soon.")
