from __future__ import annotations

import json
import random
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from itertools import product
from math import log, sqrt
from typing import Any
from urllib import error, parse, request


@dataclass
class OptimizationResult:
    best_params: dict[str, Any]
    best_score: float
    trials: list[dict[str, Any]]


class LLMAssistedRLOptimizer:
    """Q-learning + UCB optimizer with optional LLM-guided exploration priors."""

    def __init__(
        self,
        parameter_space: dict[str, list[Any]],
        *,
        alpha: float = 0.25,
        epsilon: float = 0.15,
        ucb_c: float = 1.2,
        random_seed: int = 7,
        llm_provider: str = "openai_compatible",
        llm_endpoint: str | None = None,
        llm_api_key: str | None = None,
        llm_model: str | None = None,
    ):
        if not parameter_space:
            msg = "parameter_space cannot be empty"
            raise ValueError(msg)

        self.parameter_space = parameter_space
        self.alpha = alpha
        self.epsilon = epsilon
        self.ucb_c = ucb_c
        self.random = random.Random(random_seed)

        self.action_grid = self._build_action_grid(parameter_space)
        self.q_values = [0.0 for _ in self.action_grid]
        self.action_counts = [0 for _ in self.action_grid]
        self.total_steps = 0

        self.llm_provider = llm_provider.strip().lower()
        self.llm_endpoint = llm_endpoint
        self.llm_api_key = llm_api_key
        self.llm_model = llm_model

    def optimize(
        self,
        evaluate_fn: Callable[[dict[str, Any]], tuple[float, dict[str, Any]]],
        budget: int,
    ) -> OptimizationResult:
        if budget <= 0:
            msg = "budget must be > 0"
            raise ValueError(msg)

        best_score = float("-inf")
        best_params: dict[str, Any] = {}
        trials: list[dict[str, Any]] = []

        for step in range(1, budget + 1):
            action_idx = self._select_action(trials)
            params = self.action_grid[action_idx]

            score, details = evaluate_fn(params)
            self.total_steps += 1
            self.action_counts[action_idx] += 1

            current_q = self.q_values[action_idx]
            self.q_values[action_idx] = current_q + self.alpha * (score - current_q)

            trial = {
                "step": step,
                "timestamp_utc": datetime.utcnow().isoformat(),
                "action_index": action_idx,
                "params": params,
                "score": score,
                "q_value": self.q_values[action_idx],
                "details": details,
            }
            trials.append(trial)

            if score > best_score:
                best_score = score
                best_params = params

        return OptimizationResult(best_params=best_params, best_score=best_score, trials=trials)

    def _select_action(self, trials: list[dict[str, Any]]) -> int:
        # Explore under-sampled actions first.
        unseen = [i for i, count in enumerate(self.action_counts) if count == 0]
        if unseen:
            llm_pick = self._llm_prior_pick(trials, unseen)
            if llm_pick is not None:
                return llm_pick
            return self.random.choice(unseen)

        if self.random.random() < self.epsilon:
            llm_pick = self._llm_prior_pick(trials, list(range(len(self.action_grid))))
            if llm_pick is not None:
                return llm_pick
            return self.random.randrange(len(self.action_grid))

        scores: list[float] = []
        for idx, q_value in enumerate(self.q_values):
            count = self.action_counts[idx]
            bonus = self.ucb_c * sqrt(log(self.total_steps + 1) / count)
            scores.append(q_value + bonus)

        max_score = max(scores)
        best_indices = [i for i, value in enumerate(scores) if value == max_score]
        if len(best_indices) == 1:
            return best_indices[0]

        llm_pick = self._llm_prior_pick(trials, best_indices)
        if llm_pick is not None:
            return llm_pick
        return self.random.choice(best_indices)

    def _llm_prior_pick(self, trials: list[dict[str, Any]], candidates: list[int]) -> int | None:
        if not self.llm_model:
            return None

        top_trials = sorted(trials, key=lambda t: t["score"], reverse=True)[:5]
        candidate_payload = [
            {
                "action_index": i,
                "params": self.action_grid[i],
                "q_value": round(self.q_values[i], 6),
                "count": self.action_counts[i],
            }
            for i in candidates[:20]
        ]

        prompt = {
            "instruction": (
                "Analyze the top_trials to identify which parameter combinations yield the best risk-adjusted returns. "
                "Then, evaluate the candidates and pick exactly one action_index that is most likely to improve the reward. "
                "Provide a short reasoning for your choice."
            ),
            "top_trials": top_trials,
            "candidates": candidate_payload,
            "response_schema": {"reasoning": "string", "action_index": "int"},
        }

        try:
            if self.llm_provider == "gemini":
                payload = self._request_gemini(prompt)
            else:
                payload = self._request_openai_compatible(prompt)

            action_index = self._extract_action_index(payload)
            if action_index in candidates:
                return int(action_index)
            return None
        except (error.URLError, error.HTTPError, TimeoutError, json.JSONDecodeError, ValueError):
            return None

    def _request_openai_compatible(self, prompt: dict[str, Any]) -> dict[str, Any]:
        if not self.llm_endpoint:
            raise ValueError("llm_endpoint is required for openai_compatible provider")

        headers = {"Content-Type": "application/json"}
        if self.llm_api_key:
            headers["Authorization"] = f"Bearer {self.llm_api_key}"

        body = json.dumps({"model": self.llm_model, "input": prompt}).encode("utf-8")
        req = request.Request(self.llm_endpoint, data=body, headers=headers, method="POST")

        with request.urlopen(req, timeout=12) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _request_gemini(self, prompt: dict[str, Any]) -> dict[str, Any]:
        if not self.llm_api_key:
            raise ValueError("llm_api_key is required for gemini provider")

        base_endpoint = self.llm_endpoint or (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.llm_model}:generateContent"
        )
        query = parse.urlencode({"key": self.llm_api_key})
        endpoint = f"{base_endpoint}?{query}"

        prompt_text = json.dumps(prompt, ensure_ascii=True)
        body = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": (
                                "Select one action_index from candidate actions. Return ONLY JSON with shape "
                                '{"reasoning": "<str>", "action_index": <int>}.\\n' + prompt_text
                            )
                        }
                    ],
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
            },
        }

        req = request.Request(
            endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=12) as resp:
            return json.loads(resp.read().decode("utf-8"))

    @staticmethod
    def _extract_action_index(payload: dict[str, Any]) -> int | None:
        if "action_index" in payload:
            return int(payload["action_index"])
        if "output" in payload and isinstance(payload["output"], dict):
            if "action_index" in payload["output"]:
                return int(payload["output"]["action_index"])
        if "choices" in payload and isinstance(payload["choices"], list) and payload["choices"]:
            first = payload["choices"][0]
            if isinstance(first, dict):
                content = first.get("message", {}).get("content")
                if isinstance(content, str):
                    parsed = LLMAssistedRLOptimizer._parse_json_content(content)
                    return int(parsed["action_index"])
        candidates = payload.get("candidates")
        if isinstance(candidates, list) and candidates:
            first = candidates[0]
            if isinstance(first, dict):
                content = first.get("content", {})
                if isinstance(content, dict):
                    parts = content.get("parts")
                    if isinstance(parts, list) and parts:
                        first_part = parts[0]
                        if isinstance(first_part, dict):
                            text = first_part.get("text")
                            if isinstance(text, str):
                                parsed = LLMAssistedRLOptimizer._parse_json_content(text)
                                return int(parsed["action_index"])
        return None

    @staticmethod
    def _parse_json_content(content: str) -> dict[str, Any]:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            cleaned = cleaned.replace("json", "", 1).strip()
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            cleaned = cleaned[start : end + 1]
        return json.loads(cleaned)

    @staticmethod
    def _build_action_grid(parameter_space: dict[str, list[Any]]) -> list[dict[str, Any]]:
        keys = list(parameter_space.keys())
        values = [parameter_space[key] for key in keys]
        if any(not vals for vals in values):
            msg = "All parameter lists must be non-empty"
            raise ValueError(msg)

        actions: list[dict[str, Any]] = []
        for combo in product(*values):
            actions.append(dict(zip(keys, combo, strict=True)))
        return actions
