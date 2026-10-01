import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from promptops.cli import app
from promptops.eval.rag_harness import RAGHarness
from promptops.eval.failures import classify_failures
from promptops.store import db


INPUT = {"question": "What is the return window?", "contexts": [
    {"id": "policy", "text": "Returns are accepted within 30 days."}],
    "expected_citations": ["policy"]}


def score(output):
    return asyncio.run(RAGHarness().evaluate(INPUT, output, "Returns are accepted within 30 days.", None))


def test_rag_supported_answer():
    result = score("Returns are accepted within 30 days. [policy]")
    assert result.score == 1
    assert result.criteria["unsupported_claim_rate"] == 0


@pytest.mark.parametrize("output,criterion", [
    ("Returns are accepted within 30 days.", "citation_coverage"),
    ("Returns are accepted within 90 days. [policy]", "faithfulness"),
    ("Returns are accepted within 30 days. [invented]", "citation_coverage"),
    ("Returns are accepted within 30 days. [policy] Free shipping forever.", "faithfulness"),
    ("", "answer_relevance"),
])
def test_rag_detects_failures(output, criterion):
    result = score(output)
    assert result.score < 0.85
    assert result.criteria[criterion] < 1


def test_rag_requires_sources():
    with pytest.raises(ValueError):
        asyncio.run(RAGHarness().evaluate({}, "answer", "answer", None))


@pytest.mark.parametrize("rate,expected_exit", [(1.0, 0), (0.85, 0), (0.5, 1)])
def test_ci_threshold(tmp_path, monkeypatch, rate, expected_exit):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "runs.db")
    runner = AsyncMock(return_value={"run_id": 1, "pass_rate": rate,
                                   "avg_objective": 0.8, "avg_judge_score": 0.9})
    with patch("promptops.cli.run_dataset", runner), patch("promptops.cli.make_adapter"):
        result = CliRunner().invoke(app, ["ci", "--suite", "examples/rag/suite.json",
            "--prompt", "optimized", "--harness", "rag", "--min-pass-rate", "0.85"])
    assert result.exit_code == expected_exit, result.output
    assert "Pass rate:" in result.output
    assert "Average objective:" in result.output


def test_ci_empty_suite_is_error(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "runs.db")
    suite = tmp_path / "empty.json"
    suite.write_text(json.dumps({"cases": []}))
    result = CliRunner().invoke(app, ["ci", "--suite", str(suite), "--prompt", "optimized"])
    assert result.exit_code == 2
    assert "no cases" in result.output


def test_failure_taxonomy_and_budgets():
    labels = classify_failures(passed=False, criteria={"faithfulness": 0, "citation_coverage": 0,
        "completeness": 0, "answer_relevance": 0, "safety": 0},
        metrics={"format_valid": False, "latency_ms": 20, "cost_usd": 2}, output="too many words",
        budgets={"max_latency_ms": 10, "max_cost_usd": 1, "max_output_words": 2})
    assert set(labels) == {"hallucination", "missing_citation", "incomplete_answer",
        "wrong_or_irrelevant_answer", "unsafe_output", "format_violation",
        "latency_regression", "cost_regression", "verbosity"}


@pytest.mark.parametrize("variant,expected_exit", [("baseline", 1), ("optimized", 0)])
def test_offline_replay_persists_results(tmp_path, monkeypatch, variant, expected_exit):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "runs.db")
    monkeypatch.setenv("MLFLOW_TRACKING_URI", str(tmp_path / "mlruns"))
    monkeypatch.setenv("MLFLOW_ALLOW_FILE_STORE", "true")
    result = CliRunner().invoke(app, ["ci", "--suite", "examples/rag/suite.json",
        "--prompt", variant, "--harness", "rag", "--replay",
        f"examples/rag/{variant}-responses.json"])
    assert result.exit_code == expected_exit, result.output
    run = db.recent_runs()[0]
    assert run["gate_status"] == ("passed" if expected_exit == 0 else "failed")
    rows = db.get_run_results(run["id"])
    assert len(rows) == 4
    assert rows[1]["failure_labels"] == (["missing_citation"] if variant == "baseline" else [])
    assert run["aggregate_metrics"]["citation_coverage"] == pytest.approx(0.25 if variant == "baseline" else 1)


@pytest.mark.parametrize("selector", ["named-suite", "1"])
def test_ci_stored_suite(tmp_path, monkeypatch, selector):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "runs.db")
    db.init_db()
    suite_id = db.create_suite("named-suite")
    db.add_suite_case(suite_id, INPUT, expected="Returns are accepted within 30 days.")
    runner = AsyncMock(return_value={"run_id": 1, "pass_rate": 1,
                                   "avg_objective": 0.8, "avg_judge_score": 0.9})
    with patch("promptops.cli.run_dataset", runner), patch("promptops.cli.make_adapter"):
        result = CliRunner().invoke(app, ["ci", "--suite", selector, "--prompt", "optimized", "--harness", "rag"])
    assert result.exit_code == 0, result.output
    assert runner.call_args.kwargs["suite_id"] == suite_id


def test_api_rag_registration():
    from fastapi.testclient import TestClient
    from promptops.api.app import app as api
    from promptops.tests.testcase import TestCase
    with patch("promptops.api.app.demo_dataset", return_value=[TestCase(input=INPUT, expected="30 days")]), patch("promptops.api.app.run_dataset", AsyncMock(return_value={"run_id": 1})) as runner:
        response = TestClient(api).post("/run", json={"prompt": {}, "eval_harness": "rag"})
    assert response.status_code == 200
    assert isinstance(runner.call_args.kwargs["harness"], RAGHarness)


def test_unknown_cost_is_not_reported_as_zero():
    from promptops.eval.metrics import aggregate_eval_metrics, compute_metrics
    metric = compute_metrics(1, 10, 10, 10, 4096, task_success=True)
    result = aggregate_eval_metrics([metric])
    assert result.cost_per_attempted_task is None
    assert result.cost_per_successful_task is None
