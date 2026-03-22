# Setup Guide

This guide standardizes local setup for professional strategy development, backtesting, and validation.

## Prerequisites

- Python 3.12
- uv package manager
- Git

## 1) Install Dependencies

From repository root:

uv sync --group dev

## 2) Configure Environment

Optional, for local default parameters:

1. Copy .env.example to .env
2. Adjust symbol, risk, and safety toggles as needed

## 3) Quality Gate Commands

Run all checks before committing:

- uv run ruff check .
- uv run ruff format --check .
- uv run mypy core strategies app.py main.py
- uv run pytest

## 4) Run the System

- Streamlit UI:
  - uv run streamlit run app.py
- CLI pipeline:
  - uv run python main.py

## 5) VS Code Productivity

Workspace includes:

- .vscode/extensions.json
- .vscode/tasks.json

Use VS Code task runner for install, lint, typing, test, and app launch.

## 6) CI Expectations

GitHub Actions workflow in .github/workflows/ci.yml enforces:

- Ruff lint and format check
- Mypy static typing check
- Pytest suite

## 7) Professional Backtesting Controls

Before trusting results:

1. Validate signal contract: only -1/0/1.
2. Ensure execution timing avoids look-ahead bias.
3. Reconcile final equity with cumulative net PnL.
4. Confirm metric keys used by UI remain stable.
5. Keep data quality checks in place (OHLC consistency, sorted timestamps).

