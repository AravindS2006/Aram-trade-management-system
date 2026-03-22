from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

try:
    import vectorbt as vbt  # noqa: F401
    HAS_VECTORBT = True
except Exception:
    HAS_VECTORBT = False

from core.backtester import IntradayBacktester
from core.data_handler import DataHandler
from strategies.intraday_momentum_strategy import IntradayMomentumStrategy
from strategies.sample_strategy import VWAPCrossStrategy

# Force pandas to use Python string storage to avoid PyArrow LargeUtf8 type errors in Streamlit.
pd.options.mode.string_storage = "python"

st.set_page_config(page_title="Aram Backtest Engine", page_icon="📈", layout="wide")


def _format_for_display(df: pd.DataFrame) -> pd.DataFrame:
    display_df = df.copy()
    datetime_cols = display_df.select_dtypes(
        include=["datetime64[ns, UTC]", "datetime64[ns]"]
    ).columns
    for col in datetime_cols:
        display_df[col] = pd.to_datetime(display_df[col], errors="coerce").dt.strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    float_cols = display_df.select_dtypes(include=["float", "float64", "float32"]).columns
    for col in float_cols:
        display_df[col] = display_df[col].map(
            lambda x: f"{x:.2f}" if pd.notnull(x) else ""
        )

    return display_df.astype(str).astype(object)


def _build_strategy(strategy_choice: str, df: pd.DataFrame):
    if strategy_choice == "Intraday Momentum (Proven Indian Mkt)":
        return IntradayMomentumStrategy(
            df,
            params={
                "supertrend_period": 10,
                "supertrend_multiplier": 3.0,
                "rsi_period": 14,
                "ema_period": 9,
            },
        )

    return VWAPCrossStrategy(df, params={"rsi_period": 14})


def _load_data(
    handler: DataHandler,
    ticker: str,
    start_date: date,
    end_date: date,
    interval: str,
) -> pd.DataFrame:
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    try:
        return handler.fetch_data(ticker, start_str, end_str, interval=interval)
    except Exception as exc:
        st.warning(f"Live fetch failed ({exc}). Falling back to sample CSV.")
        sample_path = Path(__file__).parent / "data" / "RELIANCE_trades.csv"
        if sample_path.exists():
            return handler.load_csv(str(sample_path))
        return pd.DataFrame()


def _build_equity_curve_figure(
    tearsheet: pd.DataFrame,
    equity_series: pd.Series,
    initial_capital: float,
) -> go.Figure:
    fig = go.Figure()

    if isinstance(equity_series.index, pd.DatetimeIndex) and len(equity_series) > 0:
        if "Entry Time" in tearsheet.columns:
            start_time = pd.to_datetime(tearsheet["Entry Time"].iloc[0], errors="coerce")
            if pd.isna(start_time):
                start_time = equity_series.index[0] - timedelta(minutes=1)
        else:
            start_time = equity_series.index[0] - timedelta(minutes=1)

        plot_x = [start_time] + list(equity_series.index)
        plot_y = [initial_capital] + list(equity_series.values)
    else:
        plot_x = [0] + list(range(1, len(equity_series) + 1))
        plot_y = [initial_capital] + list(equity_series.values)

    fig.add_trace(
        go.Scatter(
            x=plot_x,
            y=plot_y,
            mode="lines+markers",
            name="Equity",
            line=dict(color="#0E7C86", width=2),
            marker=dict(size=4, color="#0E7C86"),
        )
    )
    fig.update_layout(
        template="plotly_white",
        xaxis_title="Time",
        yaxis_title="Equity",
        margin=dict(l=10, r=10, b=10, t=30),
        height=420,
    )
    return fig


def main():
    st.title("Aram Trade Management System")
    st.caption("Structured intraday backtesting with portfolio metrics and trade logs")

    st.sidebar.header("Configuration")
    with st.sidebar.form("backtest_config"):
        ticker = st.text_input("Ticker Symbol", value="RELIANCE.NS").strip()
        strategy_choice = st.selectbox(
            "Select Strategy",
            options=[
                "Intraday Momentum (Proven Indian Mkt)",
                "VWAP Cross (Sample)",
            ],
            index=0,
        )

        start_date = st.date_input("Start Date", value=datetime.now() - timedelta(days=7))
        end_date = st.date_input("End Date", value=datetime.now())
        interval = st.selectbox(
            "Timeframe", options=["1m", "2m", "5m", "15m", "30m", "1h", "1d"], index=0
        )

        initial_capital = st.number_input("Initial Capital", value=100000.0, min_value=1.0)

        st.subheader("Risk Management")
        risk_pct = st.slider("Risk Per Trade %", 0.1, 5.0, 0.5) / 100
        sl_pct = st.slider("Stop Loss %", 0.1, 5.0, 1.0) / 100
        tp_pct = st.slider("Take Profit %", 0.1, 10.0, 2.0) / 100

        run_clicked = st.form_submit_button("Run Backtest", use_container_width=True)

    if not run_clicked:
        st.info("Set parameters in the left panel and click Run Backtest.")
        return

    if not ticker:
        st.error("Ticker symbol is required.")
        return

    if not isinstance(strategy_choice, str) or not strategy_choice:
        st.error("Strategy selection is invalid.")
        return

    if not isinstance(interval, str) or not interval:
        st.error("Timeframe selection is invalid.")
        return

    if not isinstance(start_date, date) or not isinstance(end_date, date):
        st.error("Please provide valid start and end dates.")
        return

    if start_date > end_date:
        st.error("Start Date must be before End Date.")
        return

    with st.spinner("Fetching data and running backtest..."):
        handler = DataHandler(data_dir=Path(__file__).parent / "data")
        df = _load_data(handler, ticker, start_date, end_date, interval)

        if df is None or df.empty:
            st.error("No data available for the selected inputs.")
            return

        strategy = _build_strategy(strategy_choice, df)
        data_with_signals = strategy.get_data_with_signals()

        backtester = IntradayBacktester(
            data_with_signals,
            initial_capital=initial_capital,
            risk_per_trade_pct=risk_pct,
            sl_pct=sl_pct,
            tp_pct=tp_pct,
        )
        tearsheet, metrics = backtester.run()

    st.success(f"Loaded {len(df)} candles for {ticker}")

    signal_count = int((data_with_signals["signal"] != 0).sum()) if "signal" in data_with_signals.columns else 0
    overview_cols = st.columns(4)
    overview_cols[0].metric("Signals Generated", f"{signal_count}")
    overview_cols[1].metric("Total Trades", str(metrics.get("Total Trades", 0)))
    overview_cols[2].metric("Total Return", str(metrics.get("Total Return %", "0.00%")))
    overview_cols[3].metric("Win Rate", str(metrics.get("Win Rate %", "0.00%")))

    if tearsheet is None or tearsheet.empty:
        st.warning("No trades executed for these parameters.")
        st.dataframe(_format_for_display(data_with_signals.tail(200)), use_container_width=True)
        return

    if "Exit Time" in tearsheet.columns:
        tearsheet["Exit Time"] = pd.to_datetime(tearsheet["Exit Time"], errors="coerce")
        tearsheet = tearsheet.sort_values("Exit Time")
        equity_series = tearsheet.set_index("Exit Time")["Equity"]
    else:
        equity_series = tearsheet["Equity"]

    returns = equity_series.pct_change().replace([np.inf, -np.inf], np.nan).dropna()

    core_metrics_df = pd.DataFrame(list(metrics.items()), columns=["Metric", "Value"]).set_index("Metric")

    vbt_metrics_df = pd.DataFrame()
    if HAS_VECTORBT and len(returns) > 0:
        try:
            stats = returns.vbt.returns(freq="D").stats()
            vbt_dict = {}
            for k, v in stats.items():
                if pd.isna(v):
                    vbt_dict[str(k)] = "NaN"
                elif isinstance(v, (float, np.floating)):
                    vbt_dict[str(k)] = f"{v:.3f}"
                elif isinstance(v, pd.Timedelta):
                    vbt_dict[str(k)] = f"{v.days} days"
                else:
                    vbt_dict[str(k)] = str(v)
            vbt_metrics_df = pd.DataFrame(list(vbt_dict.items()), columns=["Metric", "Value"]).set_index("Metric")
        except Exception as exc:
            st.warning(f"VectorBT stats could not be computed: {exc}")

    tab_dashboard, tab_log, tab_data = st.tabs(["Dashboard", "Trade Log", "Raw Data"])

    with tab_dashboard:
        col_left, col_right = st.columns([1, 2])

        with col_left:
            st.subheader("Core Metrics")
            st.dataframe(_format_for_display(core_metrics_df), use_container_width=True, height=420)

            st.subheader("Advanced Metrics")
            if not vbt_metrics_df.empty:
                st.dataframe(_format_for_display(vbt_metrics_df), use_container_width=True, height=300)
            else:
                if HAS_VECTORBT:
                    st.info("Not enough return points for advanced stats.")
                else:
                    st.info("Install vectorbt to view advanced metrics.")

        with col_right:
            st.subheader("Equity Curve")
            fig = _build_equity_curve_figure(tearsheet, equity_series, initial_capital)
            st.plotly_chart(fig, use_container_width=True)

    with tab_log:
        st.subheader("Trade Log")
        st.dataframe(_format_for_display(tearsheet), use_container_width=True, height=520)

    with tab_data:
        st.subheader("Processed Data With Signals")
        st.dataframe(_format_for_display(data_with_signals), use_container_width=True, height=520)

if __name__ == "__main__":
    main()
