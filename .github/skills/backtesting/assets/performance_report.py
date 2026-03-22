"""
performance_report.py — Backtest Performance Reporting Utility
=============================================================
Located in: .github/skills/backtesting/assets/

Generate summary statistics and charts from backtest results.
Usage:
    from performance_report import generate_report
    generate_report(results, output_dir="output/")
"""

import os
import math
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from typing import Optional


# ---------------------------------------------------------------------------
# Core Statistics
# ---------------------------------------------------------------------------

def compute_stats(results: dict) -> dict:
    """
    Compute key performance statistics from backtest results.

    Args:
        results: dict with keys:
            - 'returns'         : pd.Series of daily returns (decimal)
            - 'portfolio_value' : pd.Series of NAV over time
            - 'trades'          : list of trade dicts {entry_price, exit_price, pnl, ...}
            - 'starting_capital': float

    Returns:
        dict of computed statistics.
    """
    returns: pd.Series = results["returns"].dropna()
    nav: pd.Series = results["portfolio_value"]
    trades: list = results.get("trades", [])
    starting_capital: float = results.get("starting_capital", nav.iloc[0])

    # Return metrics
    total_return = (nav.iloc[-1] - starting_capital) / starting_capital
    ann_return = _annualized_return(returns)
    ann_vol = returns.std() * math.sqrt(252)
    sharpe = ann_return / ann_vol if ann_vol != 0 else 0.0
    sortino = _sortino_ratio(returns)
    max_dd = _max_drawdown(nav)

    # Trade metrics
    n_trades = len(trades)
    wins = [t for t in trades if t.get("pnl", 0) > 0]
    losses = [t for t in trades if t.get("pnl", 0) <= 0]
    win_rate = len(wins) / n_trades if n_trades else 0.0
    avg_win = np.mean([t["pnl"] for t in wins]) if wins else 0.0
    avg_loss = abs(np.mean([t["pnl"] for t in losses])) if losses else 0.0
    profit_factor = (avg_win * len(wins)) / (avg_loss * len(losses)) if losses else float("inf")

    return {
        "total_return_pct": total_return * 100,
        "annualized_return_pct": ann_return * 100,
        "annualized_volatility_pct": ann_vol * 100,
        "sharpe_ratio": round(sharpe, 2),
        "sortino_ratio": round(sortino, 2),
        "max_drawdown_pct": max_dd * 100,
        "total_trades": n_trades,
        "win_rate_pct": win_rate * 100,
        "profit_factor": round(profit_factor, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
    }


# ---------------------------------------------------------------------------
# Chart Generation
# ---------------------------------------------------------------------------

def generate_charts(results: dict, output_dir: str = "output/") -> list[str]:
    """
    Generate and save performance charts.

    Returns:
        List of saved file paths.
    """
    os.makedirs(output_dir, exist_ok=True)
    saved = []

    nav: pd.Series = results["portfolio_value"]
    returns: pd.Series = results["returns"].dropna()
    trades: list = results.get("trades", [])

    fig = plt.figure(figsize=(16, 10), facecolor="#1a1a2e")
    fig.suptitle("Backtest Performance Report", color="white", fontsize=16, fontweight="bold")
    gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.4, wspace=0.3)

    # 1 — Equity curve
    ax1 = fig.add_subplot(gs[0, :])
    ax1.set_facecolor("#16213e")
    ax1.plot(nav.index, nav.values, color="#4ecdc4", linewidth=1.5, label="Portfolio NAV")
    ax1.fill_between(nav.index, nav.values, nav.values.min(), alpha=0.1, color="#4ecdc4")
    ax1.set_title("Equity Curve", color="white")
    ax1.tick_params(colors="grey")
    ax1.set_xlabel("Date", color="grey")
    ax1.set_ylabel("Portfolio Value (₹)", color="grey")
    ax1.spines[:].set_color("#333")
    ax1.legend(facecolor="#16213e", labelcolor="white")

    # 2 — Drawdown
    ax2 = fig.add_subplot(gs[1, 0])
    ax2.set_facecolor("#16213e")
    cummax = nav.cummax()
    drawdown = (nav - cummax) / cummax * 100
    ax2.fill_between(drawdown.index, drawdown.values, 0, color="#e74c3c", alpha=0.7)
    ax2.set_title("Drawdown (%)", color="white")
    ax2.tick_params(colors="grey")
    ax2.set_ylabel("Drawdown %", color="grey")
    ax2.spines[:].set_color("#333")

    # 3 — Return distribution
    ax3 = fig.add_subplot(gs[1, 1])
    ax3.set_facecolor("#16213e")
    ax3.hist(returns * 100, bins=40, color="#f39c12", edgecolor="#16213e", alpha=0.8)
    ax3.axvline(0, color="white", linestyle="--", linewidth=0.8)
    ax3.set_title("Return Distribution (%)", color="white")
    ax3.tick_params(colors="grey")
    ax3.set_xlabel("Daily Return %", color="grey")
    ax3.spines[:].set_color("#333")

    chart_path = os.path.join(output_dir, "performance_charts.png")
    plt.savefig(chart_path, dpi=150, bbox_inches="tight", facecolor="#1a1a2e")
    plt.close()
    saved.append(chart_path)

    return saved


# ---------------------------------------------------------------------------
# Report Generator (main entry point)
# ---------------------------------------------------------------------------

def generate_report(
    results: dict,
    strategy_name: str = "Strategy",
    output_dir: str = "output/",
    print_summary: bool = True,
) -> dict:
    """
    Full performance report: prints stats + saves charts.

    Args:
        results       : Backtest results dict
        strategy_name : Name of strategy for labelling
        output_dir    : Directory to save charts and markdown report
        print_summary : Whether to print stats to stdout

    Returns:
        dict of computed stats
    """
    stats = compute_stats(results)
    chart_paths = generate_charts(results, output_dir)

    if print_summary:
        _print_summary(strategy_name, stats)

    _write_markdown_report(strategy_name, stats, chart_paths, output_dir)

    return stats


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------

def _annualized_return(returns: pd.Series, periods_per_year: int = 252) -> float:
    n = len(returns)
    if n == 0:
        return 0.0
    cumulative = (1 + returns).prod()
    return cumulative ** (periods_per_year / n) - 1


def _sortino_ratio(returns: pd.Series, periods_per_year: int = 252) -> float:
    ann_return = _annualized_return(returns)
    downside = returns[returns < 0]
    downside_std = downside.std() * math.sqrt(periods_per_year)
    return ann_return / downside_std if downside_std != 0 else 0.0


def _max_drawdown(nav: pd.Series) -> float:
    cummax = nav.cummax()
    drawdown = (nav - cummax) / cummax
    return drawdown.min()


def _print_summary(strategy_name: str, stats: dict) -> None:
    print(f"\n{'='*50}")
    print(f"  Performance Report — {strategy_name}")
    print(f"{'='*50}")
    print(f"  Total Return       : {stats['total_return_pct']:.2f}%")
    print(f"  Annualized Return  : {stats['annualized_return_pct']:.2f}%")
    print(f"  Annualized Vol     : {stats['annualized_volatility_pct']:.2f}%")
    print(f"  Sharpe Ratio       : {stats['sharpe_ratio']}")
    print(f"  Sortino Ratio      : {stats['sortino_ratio']}")
    print(f"  Max Drawdown       : {stats['max_drawdown_pct']:.2f}%")
    print(f"  Total Trades       : {stats['total_trades']}")
    print(f"  Win Rate           : {stats['win_rate_pct']:.1f}%")
    print(f"  Profit Factor      : {stats['profit_factor']}")
    print(f"  Avg Win / Avg Loss : ₹{stats['avg_win']} / ₹{stats['avg_loss']}")
    print(f"{'='*50}\n")


def _write_markdown_report(
    strategy_name: str, stats: dict, chart_paths: list, output_dir: str
) -> None:
    md_lines = [
        f"# Backtest Report — {strategy_name}",
        "",
        "## Summary Statistics",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total Return | {stats['total_return_pct']:.2f}% |",
        f"| Annualized Return | {stats['annualized_return_pct']:.2f}% |",
        f"| Annualized Volatility | {stats['annualized_volatility_pct']:.2f}% |",
        f"| Sharpe Ratio | {stats['sharpe_ratio']} |",
        f"| Sortino Ratio | {stats['sortino_ratio']} |",
        f"| Max Drawdown | {stats['max_drawdown_pct']:.2f}% |",
        f"| Total Trades | {stats['total_trades']} |",
        f"| Win Rate | {stats['win_rate_pct']:.1f}% |",
        f"| Profit Factor | {stats['profit_factor']} |",
        f"| Avg Win | ₹{stats['avg_win']} |",
        f"| Avg Loss | ₹{stats['avg_loss']} |",
        "",
        "## Charts",
        "",
    ]
    for path in chart_paths:
        rel = os.path.relpath(path, output_dir)
        md_lines.append(f"![Performance Charts]({rel})")

    report_path = os.path.join(output_dir, "backtest_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))
