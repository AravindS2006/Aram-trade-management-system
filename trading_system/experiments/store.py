from __future__ import annotations

import json
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd


class BacktestResultStore:
    """Filesystem-backed run store for backtest and optimization artifacts."""

    def __init__(self, root_dir: str | Path):
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root_dir / "runs_index.jsonl"

    def start_run(self, context: dict[str, Any]) -> str:
        run_id = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ") + "_" + uuid4().hex[:8]
        run_dir = self._run_dir(run_id)
        run_dir.mkdir(parents=True, exist_ok=True)

        metadata = {
            "run_id": run_id,
            "created_at_utc": datetime.utcnow().isoformat(),
            "status": "running",
            "context": context,
            "config_hash": self._stable_hash(context),
        }
        self._write_json(run_dir / "metadata.json", metadata)
        self._append_jsonl(self.index_path, metadata)
        return run_id

    def save_backtest(
        self,
        run_id: str,
        metrics: dict[str, Any],
        tearsheet: pd.DataFrame | None,
        params: dict[str, Any],
        extra: dict[str, Any] | None = None,
    ) -> None:
        run_dir = self._run_dir(run_id)
        run_dir.mkdir(parents=True, exist_ok=True)

        payload = {
            "saved_at_utc": datetime.utcnow().isoformat(),
            "metrics": metrics,
            "params": params,
            "extra": extra or {},
        }
        self._write_json(run_dir / "summary.json", payload)

        if tearsheet is not None and not tearsheet.empty:
            tearsheet.to_csv(run_dir / "tearsheet.csv", index=False)

    def append_trial(self, run_id: str, trial_payload: dict[str, Any]) -> None:
        trials_path = self._run_dir(run_id) / "trials.jsonl"
        enriched = {
            "logged_at_utc": datetime.utcnow().isoformat(),
            **trial_payload,
        }
        self._append_jsonl(trials_path, enriched)

    def finalize_run(
        self,
        run_id: str,
        status: str,
        best_score: float | None = None,
        best_params: dict[str, Any] | None = None,
        notes: str | None = None,
    ) -> None:
        run_dir = self._run_dir(run_id)
        meta_path = run_dir / "metadata.json"
        metadata = self._read_json(meta_path)
        metadata["status"] = status
        metadata["finished_at_utc"] = datetime.utcnow().isoformat()
        metadata["best_score"] = best_score
        metadata["best_params"] = best_params
        metadata["notes"] = notes
        self._write_json(meta_path, metadata)

    def _run_dir(self, run_id: str) -> Path:
        return self.root_dir / run_id

    def _write_json(self, path: Path, payload: dict[str, Any]) -> None:
        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, default=self._json_default)

    def _read_json(self, path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _append_jsonl(self, path: Path, payload: dict[str, Any]) -> None:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, default=self._json_default) + "\n")

    def _stable_hash(self, payload: dict[str, Any]) -> str:
        stable = json.dumps(payload, sort_keys=True, default=self._json_default)
        return sha256(stable.encode("utf-8")).hexdigest()

    @staticmethod
    def _json_default(value: Any) -> Any:
        if isinstance(value, (datetime, pd.Timestamp)):
            return value.isoformat()
        if isinstance(value, Path):
            return str(value)
        if hasattr(value, "item"):
            return value.item()
        return str(value)
