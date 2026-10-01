import asyncio
import json
from unittest.mock import AsyncMock

import pytest

from promptops.core.adapters.base import ModelResponse
from promptops.core.adapters.cost import cost_trace
from promptops.core.prompt import Prompt
from promptops.core.runner import run_prompt
from promptops.eval.judge import JudgeResult
from promptops.eval.rag_harness import RAGHarness, SemanticRAGHarness
from promptops.eval.release import evaluate_release_gate, ReleaseGateThresholds
INPUT = {"question": "What is the return window?", "contexts": [{"id": "policy", "text": "Returns are accepted within 30 days."}], "expected_citations": ["policy"]}


@pytest.mark.parametrize("output", [
    "30 days accepted returns within are. [policy]",
    "Returns are not accepted within 30 days. [policy]",
])
def test_extractiveness_requires_source_phrase(output):
    result = asyncio.run(RAGHarness().evaluate(INPUT, output, "Returns are accepted within 30 days.", None))
    assert result.score == 0


def semantic_response(**overrides):
    data = dict(faithfulness=1, context_relevance=1, answer_relevance=1, completeness=1,
                citation_coverage=1, safety=1, reasoning="Supported paraphrase")
    data.update(overrides)
    return ModelResponse(output=json.dumps(data))


def test_semantic_judge_accepts_paraphrase():
    adapter = AsyncMock()
    adapter.generate.return_value = semantic_response()
    result = asyncio.run(SemanticRAGHarness(adapter, "judge").evaluate(INPUT,
        "You have a month to return purchases. [policy]", "Returns are accepted within 30 days.", None))
    assert result.score == 1
    assert "untrusted" in adapter.generate.call_args.kwargs["system"]


@pytest.mark.parametrize("output", ["A month. [unknown]", "A month.", ""])
def test_semantic_judge_cannot_override_citation_checks(output):
    adapter = AsyncMock()
    adapter.generate.return_value = semantic_response()
    result = asyncio.run(SemanticRAGHarness(adapter, "judge").evaluate(INPUT, output, "30 days", None))
    assert result.score == 0


@pytest.mark.parametrize("response", ["0.9", "{}", '{"faithfulness": 2}', "not json"])
def test_semantic_judge_fails_closed(response):
    adapter = AsyncMock()
    adapter.generate.return_value = ModelResponse(output=response)
    result = asyncio.run(SemanticRAGHarness(adapter, "judge").evaluate(INPUT, "30 days [policy]", "30 days", None))
    assert result.score == 0


def test_semantic_unsupported_and_safety_labels():
    adapter = AsyncMock()
    adapter.generate.return_value = semantic_response(faithfulness=0, safety=0)
    result = asyncio.run(SemanticRAGHarness(adapter, "judge").evaluate(INPUT, "Invented fact [policy]", "30 days", None))
    assert result.score == 0
    assert result.criteria["unsupported_claim_rate"] == 1


@pytest.mark.parametrize("provider", ["openai", "anthropic", "ollama"])
def test_configured_provider_cost(provider, monkeypatch):
    monkeypatch.setenv("PROMPTOPS_TOKEN_PRICES", json.dumps({f"{provider}:model": {"input": 2, "output": 4}}))
    assert cost_trace(provider, "model", 1000, 500)["cost_usd"] == pytest.approx(0.004)
    assert cost_trace(provider, "unknown", 1000, 500) == {}
    assert cost_trace(provider, "model", None, 500) == {}


def test_generic_default_gate_and_nan_rejection():
    assert evaluate_release_gate({"task_success_rate": 1, "latency_p95_ms": 10}).passed
    assert not evaluate_release_gate({"task_success_rate": float("nan"), "latency_p95_ms": 10}).passed
    assert not evaluate_release_gate({"task_success_rate": 1, "latency_p95_ms": 10},
                                    ReleaseGateThresholds(minimums={"retrieval_precision": .8})).passed


def test_missing_regression_metric_fails_closed():
    assert not evaluate_release_gate({}, ReleaseGateThresholds(max_regression={"task_success_rate": .02}), {}).passed


@pytest.mark.parametrize("budget,response,label", [
    ({"max_latency_ms": 10}, ModelResponse(output="ok", latency_ms=20), "latency_regression"),
    ({"max_output_words": 1}, ModelResponse(output="too long"), "verbosity"),
    ({"max_cost_usd": 1}, ModelResponse(output="ok"), "cost_usd_unavailable"),
])
def test_case_budget_enforced(budget, response, label):
    from promptops.tests.testcase import TestCase
    adapter = AsyncMock()
    adapter.generate.return_value = response
    harness = AsyncMock()
    harness.evaluate.return_value = JudgeResult(score=1)
    _, metrics, info = asyncio.run(run_prompt(adapter, Prompt(name="test", model="model", system="", template="{input}"),
        TestCase(input={"input": "hi"}, rubric={"budgets": budget}), "judge", harness=harness))
    assert not info["passed"]
    assert not metrics.task_success
    assert label in info["failure_labels"]


def test_json_schema_violation_is_failure_even_with_low_threshold():
    from promptops.tests.testcase import TestCase
    adapter = AsyncMock()
    adapter.generate.return_value = ModelResponse(output='{"wrong": 3}')
    harness = AsyncMock()
    harness.evaluate.return_value = JudgeResult(score=1)
    prompt = Prompt(name="test", model="model", system="", template="{input}",
                    output_schema={"type": "object", "required": ["answer"]})
    _, metrics, info = asyncio.run(run_prompt(adapter, prompt, TestCase(input={"input": "hi"}, threshold=.1), "judge", harness=harness))
    assert metrics.format_valid is False
    assert not info["passed"]
    assert "format_violation" in info["failure_labels"]


@pytest.mark.parametrize("mode", ["rag", "rag-semantic"])
def test_api_invalid_rag_suite_rejected_before_provider_call(mode):
    from fastapi.testclient import TestClient
    from unittest.mock import patch
    from promptops.api.app import app
    with patch("promptops.api.app.run_dataset") as runner:
        response = TestClient(app).post("/run", json={"prompt": {}, "eval_harness": mode})
    assert response.status_code == 400
    runner.assert_not_called()


@pytest.mark.parametrize("budgets", [{"max_cost_usd": -1}, {"max_latency_ms": float("nan")}, {"typo": 2}])
def test_invalid_budget_configuration_rejected(budgets):
    from promptops.tests.testcase import TestCase
    with pytest.raises(ValueError):
        TestCase(input={}, rubric={"budgets": budgets})


def test_openai_adapter_populates_configured_cost(monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import patch
    from promptops.core.adapters.openai import OpenAIAdapter
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=AsyncMock(
        return_value=SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))],
            usage=SimpleNamespace(prompt_tokens=1000, completion_tokens=500, total_tokens=1500))))))
    client.close = AsyncMock()
    monkeypatch.setenv("PROMPTOPS_TOKEN_PRICES", '{"openai:model": {"input": 2, "output": 4}}')
    with patch("openai.AsyncOpenAI", return_value=client):
        result = asyncio.run(OpenAIAdapter(api_key="test-key").generate("model", "system", "prompt", {}))
    assert result.raw["cost_usd"] == pytest.approx(.004)
    assert result.raw["cost_source"] == "configured_token_rate_estimate"



def test_ollama_generation_options_use_options_object():
    from unittest.mock import MagicMock, patch
    from promptops.core.adapters.ollama import OllamaAdapter
    response = MagicMock()
    response.json.return_value = {"response": "ok"}
    client = AsyncMock()
    client.post.return_value = response
    with patch("httpx.AsyncClient") as factory:
        factory.return_value.__aenter__ = AsyncMock(return_value=client)
        factory.return_value.__aexit__ = AsyncMock(return_value=False)
        asyncio.run(OllamaAdapter().generate("model", "system", "prompt",
            {"max_tokens": 32, "temperature": 0, "seed": 42, "format": "json"}))
    payload = client.post.call_args.kwargs["json"]
    assert payload["options"] == {"num_predict": 32, "temperature": 0, "seed": 42}
    assert payload["format"] == "json"
    assert "num_predict" not in payload


def test_parallel_evaluations_keep_mlflow_results_separate(tmp_path, monkeypatch):
    import mlflow
    from mlflow.tracking import MlflowClient
    from promptops.store import db
    from promptops.core.runner import run_dataset
    from promptops.tests.testcase import TestCase
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "runs.db")
    monkeypatch.setenv("MLFLOW_ALLOW_FILE_STORE", "true")
    adapter = AsyncMock()
    adapter.health_check.return_value = True
    async def generate(**kwargs):
        await asyncio.sleep(.01)
        return ModelResponse(output=kwargs["prompt"], prompt_tokens=1, completion_tokens=1)
    adapter.generate.side_effect = generate
    harness = AsyncMock()
    harness.evaluate.return_value = JudgeResult(score=1)
    tracking_uri = str(tmp_path / "mlruns")
    monkeypatch.setenv("MLFLOW_TRACKING_URI", tracking_uri)
    async def evaluate():
        return await asyncio.gather(*[
            run_dataset(adapter, Prompt(name=name, model="test", system="", template=name),
                        [TestCase(input={})], "judge", harness=harness)
            for name in ("alpha", "beta")
        ])
    results = asyncio.run(evaluate())
    client = MlflowClient(tracking_uri=tracking_uri)
    for name, result in zip(("alpha", "beta"), results):
        row = db.get_run(result["run_id"])
        tracked = client.get_run(row["run_id"])
        assert tracked.data.params["prompt_name"] == name
        assert tracked.data.metrics["pass_rate"] == 1
        artifact = client.download_artifacts(row["run_id"], "outputs.txt")
        from pathlib import Path
        assert Path(artifact).read_text() == name
