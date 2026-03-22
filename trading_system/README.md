# Trading System Structure

This package separates reusable strategy logic from execution mode.

## Layout

- `trading_system/shared/`
  - Shared strategies and future shared data/indicator/risk components.
- `trading_system/backtest/`
  - Backtest engine adapters (currently wraps `core.backtester.IntradayBacktester`).
- `trading_system/forwardtest/`
  - Forward-test event loop scaffolding.
- `trading_system/live/`
  - Live-trading event loop scaffolding.

## Import Rules

- New code should import strategies from `trading_system.shared.strategies`.
- Existing legacy modules in `strategies/` remain supported.
- Backtest app/CLI run from repository root and can progressively migrate to `trading_system/backtest` APIs.

## Why this avoids confusion

- One strategy namespace for all modes (`shared/strategies`).
- Execution concerns split by mode (`backtest`, `forwardtest`, `live`).
- Future systems can be added without moving strategy files again.

