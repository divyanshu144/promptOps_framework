from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from promptops.api.app import app
from promptops.core.prompt import Prompt

client = TestClient(app)


OPTIMIZE_PAYLOAD = {
    "prompt": {
        "name": "test",
        "system": "You are helpful.",
        "template": "{input}",
        "model": "llama3.1",
        "params": {"temperature": 0.2, "max_tokens": 200},
        "context_limit": 4096,
        "provider": "ollama",
    },
    "judge_model": "llama3.1",
    "iterations": 1,
    "use_rewriter": False,
}


def _prompt() -> Prompt:
    return Prompt(**OPTIMIZE_PAYLOAD["prompt"])


def _optimizer_result() -> dict:
    return {
        "baseline_result": {
            "avg_judge_score": 0.6,
            "avg_objective": 0.5,
            "pass_rate": 0.5,
            "outputs": ["base"],
        },
        "best_prompt": _prompt(),
        "best_result": {
            "avg_judge_score": 0.9,
            "avg_objective": 0.8,
            "pass_rate": 1.0,
            "outputs": ["best"],
        },
        "comparison": {
            "baseline_prompt_name": "test",
            "best_prompt_name": "test",
            "objective_delta": 0.3,
            "judge_score_delta": 0.3,
            "pass_rate_delta": 0.5,
            "improved": True,
        },
    }


def test_optimize_endpoint_returns_baseline_and_comparison():
    with patch("promptops.api.app.make_adapter", return_value=MagicMock()), patch(
        "promptops.api.app.optimize_prompt", new=AsyncMock(return_value=_optimizer_result())
    ):
        response = client.post("/optimize", json=OPTIMIZE_PAYLOAD)

    assert response.status_code == 200
    data = response.json()
    assert data["baseline_result"]["pass_rate"] == pytest.approx(0.5)
    assert data["best_result"]["pass_rate"] == pytest.approx(1.0)
    assert data["comparison"]["pass_rate_delta"] == pytest.approx(0.5)


def test_optimize_endpoint_preserves_suite_case_thresholds():
    suite_cases = [
        {
            "input": {"input": "q1"},
            "expected": "a1",
            "rubric": {"quality": 1.0},
            "threshold": 0.85,
        }
    ]

    with patch("promptops.api.app.make_adapter", return_value=MagicMock()), patch(
        "promptops.api.app.get_suite_cases", return_value=suite_cases
    ), patch("promptops.api.app.optimize_prompt", new=AsyncMock(return_value=_optimizer_result())) as mock_opt:
        response = client.post("/optimize", json={**OPTIMIZE_PAYLOAD, "suite_id": 123})

    assert response.status_code == 200
    testcase = mock_opt.call_args.kwargs["testcases"][0]
    assert testcase.threshold == pytest.approx(0.85)
