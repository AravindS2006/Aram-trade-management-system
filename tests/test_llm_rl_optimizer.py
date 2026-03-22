from trading_system.optimization import LLMAssistedRLOptimizer


def test_optimizer_finds_high_reward_region() -> None:
    optimizer = LLMAssistedRLOptimizer(
        parameter_space={
            "sl_pct": [0.005, 0.01, 0.015],
            "tp_pct": [0.015, 0.02, 0.03],
        },
        random_seed=42,
        epsilon=0.1,
    )

    target = {"sl_pct": 0.01, "tp_pct": 0.03}

    def evaluate(params: dict) -> tuple[float, dict]:
        # Smooth reward surface with a known optimum.
        score = 2.0
        score -= abs(params["sl_pct"] - target["sl_pct"]) * 200
        score -= abs(params["tp_pct"] - target["tp_pct"]) * 100
        return score, {"ok": True}

    result = optimizer.optimize(evaluate_fn=evaluate, budget=20)

    assert result.best_score > 1.0
    assert result.best_params["tp_pct"] == 0.03
    assert len(result.trials) == 20
