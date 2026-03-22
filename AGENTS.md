---
name: agents-registry
description: "Registry of custom agents for the Aram Trade Management System"
---

# Custom Agents

Custom agents for specialized workflows in the trade management system. Each agent is optimized for a specific domain while maintaining access to the main codebase.

## Available Agents

### Master Agent
- **Name**: `master-agent`
- **Path**: `.github/agents/master-agent.agent.md`
- **Use When**: Need cross-module orchestration across strategy, backtester, portfolio, Streamlit, and performance/debug workflows.
- **Capabilities**: System-wide analysis, coordinated refactors, root-cause diagnosis across layers.
- **Tool Restrictions**: Full access including subagent orchestration.

### Strategy Developer
- **Name**: `strategy-dev`
- **Path**: `.github/agents/strategy-dev.agent.md`
- **Use When**: Creating/debugging/tuning strategy files in `backtest_system/strategies`.
- **Capabilities**: Strategy implementation, signal validation, backtest-driven tuning.
- **Tool Restrictions**: Full access to read, edit, search, and run terminal commands

### Data Analyst
- **Name**: `data-analyst`
- **Path**: `.github/agents/data-analyst.agent.md`
- **Use When**: EDA, anomaly detection, data integrity checks, and report generation.
- **Capabilities**: Dataset validation, statistical analysis, insight reporting.
- **Tool Restrictions**: Full access to read, edit, search, and run terminal commands

### Performance Optimizer
- **Name**: `perf-optimizer`
- **Path**: `.github/agents/perf-optimizer.agent.md`
- **Use When**: Profiling and optimizing slow backtests, indicators, or memory-heavy flows.
- **Capabilities**: Profiling, benchmarking, optimization and parity validation.
- **Tool Restrictions**: Full access to read, edit, search, and run terminal commands

### Backtest Debugger
- **Name**: `backtest-debugger`
- **Path**: `.github/agents/backtest-debugger.agent.md`
- **Use When**: Diagnosing execution/PNL mismatches, portfolio reconciliation issues, and backtest failures.
- **Capabilities**: Bar-by-bar trace, trade lifecycle diagnostics, targeted bug fixes.
- **Tool Restrictions**: Full access to read, edit, search, and run terminal commands

## How to Invoke

Use `@AgentName` in chat or type `/agent-name` as a slash command.

Example: `@strategy-dev help me debug my MACD strategy`
