from pathlib import Path

import pandas as pd

from trading_system.experiments import BacktestResultStore


def test_result_store_writes_expected_artifacts(tmp_path: Path) -> None:
    store = BacktestResultStore(tmp_path / "runs")
    run_id = store.start_run({"ticker": "RELIANCE", "strategy": "intraday"})

    tearsheet = pd.DataFrame(
        {
            "Entry Time": ["2024-01-01 09:16:00"],
            "Exit Time": ["2024-01-01 09:31:00"],
            "Net PnL": [123.45],
            "Equity": [100123.45],
        }
    )

    store.append_trial(run_id, {"score": 1.25, "params": {"sl_pct": 0.01}})
    store.save_backtest(
        run_id,
        metrics={"Total Return %": "1.23%", "Total Trades": 1},
        tearsheet=tearsheet,
        params={"execution": {"sl_pct": 0.01}},
    )
    store.finalize_run(run_id, status="completed", best_score=1.25, best_params={"sl_pct": 0.01})

    run_dir = tmp_path / "runs" / run_id
    assert (run_dir / "metadata.json").exists()
    assert (run_dir / "summary.json").exists()
    assert (run_dir / "tearsheet.csv").exists()
    assert (run_dir / "trials.jsonl").exists()
    assert (tmp_path / "runs" / "runs_index.jsonl").exists()
