import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from promptops.api.app import app

client = TestClient(app)

RUN_PAYLOAD = {
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
}

MOCK_RUN_RESULT = {
    "run_id": 1,
    "avg_judge_score": 0.8,
    "avg_objective": 0.75,
    "outputs": ["output"],
    "regression": False,
    "regression_warning": None,
}


def test_run_without_eval_harness_passes_none_harness():
    with patch("promptops.api.app.run_dataset", return_value=MOCK_RUN_RESULT) as mock_run:
        response = client.post("/run", json=RUN_PAYLOAD)

    assert response.status_code == 200
    call_kwargs = mock_run.call_args.kwargs
    assert call_kwargs.get("harness") is None


def test_run_with_deepeval_harness_constructs_deepeval_harness():
    payload = {**RUN_PAYLOAD, "eval_harness": "deepeval"}

    with patch("promptops.api.app.run_dataset", return_value=MOCK_RUN_RESULT) as mock_run, \
         patch("promptops.api.app.DeepEvalHarness") as MockDEH:
        mock_deh_instance = MagicMock()
        MockDEH.return_value = mock_deh_instance

        response = client.post("/run", json=payload)

    assert response.status_code == 200
    MockDEH.assert_called_once()
    call_kwargs = mock_run.call_args.kwargs
    assert call_kwargs.get("harness") is mock_deh_instance


def test_run_with_unknown_eval_harness_returns_400():
    payload = {**RUN_PAYLOAD, "eval_harness": "unknown_framework"}
    response = client.post("/run", json=payload)
    assert response.status_code == 400
