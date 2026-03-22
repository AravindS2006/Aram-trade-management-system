# Skill: Dashboard Development — Aram-TMS

## Framework
Streamlit (primary) + Plotly (charts)
Entry: src/dashboard/app.py
Run: streamlit run src/dashboard/app.py (port 8501)

## Pages
01_overview.py     Portfolio overview + equity curve
02_backtest.py     Backtest runner + results
03_forward_test.py DhanHQ sandbox monitor
04_strategies.py   Strategy library management
05_risk.py         Risk monitor + gauges
06_analytics.py    Performance analytics
07_settings.py     API keys + risk config

## Color Scheme (Institutional Dark)
background="#0A0E1A"  surface="#111827"  border="#1F2937"
text_primary="#F9FAFB"  text_secondary="#9CA3AF"
profit="#10B981"  loss="#EF4444"  accent="#3B82F6"  warning="#F59E0B"

## Key Patterns
```python
# Always init session state
if "key" not in st.session_state: st.session_state.key = default

# Cache expensive calls
@st.cache_data(ttl=300)
def load_results(id): return pd.read_parquet(f"data/results/backtests/{id}.parquet")

# Real-time refresh
placeholder = st.empty()
while True:
    with placeholder.container(): render_positions()
    time.sleep(30); st.rerun()
```

## Chart Templates
```python
# Equity curve
fig = go.Figure()
fig.add_trace(go.Scatter(x=dates, y=equity, name="Strategy",
    line=dict(color="#3B82F6", width=2), fill="tozeroy",
    fillcolor="rgba(59,130,246,0.05)"))
fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)", height=400, hovermode="x unified")
st.plotly_chart(fig, use_container_width=True)

# Drawdown
drawdown = (equity / equity.cummax() - 1) * 100
fig2 = go.Figure(go.Scatter(x=dates, y=drawdown, fill="tozeroy",
    fillcolor="rgba(239,68,68,0.15)", line=dict(color="#EF4444")))
```
