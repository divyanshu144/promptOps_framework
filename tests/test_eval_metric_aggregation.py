import pytest

from promptops.eval.metrics import (
    aggregate_eval_metrics,
    compute_metrics,
    score_groundedness,
    score_retrieval_precision,
    score_tool_call_accuracy,
)


def test_aggregate_eval_metrics_computes_quality_efficiency_and_latency_metrics():
    results = [
        compute_metrics(
            judge_score=0.9,
            prompt_tokens=100,
            completion_tokens=50,
            latency_ms=100,
            context_limit=4096,
            task_success=True,
            tool_call_accuracy=1.0,
            retrieval_precision=2 / 3,
            groundedness_score=0.9,
            cost_usd=0.10,
        ),
        compute_metrics(
            judge_score=0.4,
            prompt_tokens=100,
            completion_tokens=50,
            latency_ms=200,
            context_limit=4096,
            task_success=False,
            tool_call_accuracy=0.0,
            retrieval_precision=0.5,
            groundedness_score=0.4,
            cost_usd=0.20,
        ),
        compute_metrics(
            judge_score=0.8,
            prompt_tokens=100,
            completion_tokens=50,
            latency_ms=300,
            context_limit=4096,
            task_success=True,
            tool_call_accuracy=None,
            retrieval_precision=None,
            groundedness_score=0.8,
            cost_usd=0.30,
        ),
        compute_metrics(
            judge_score=0.2,
            prompt_tokens=100,
            completion_tokens=50,
            latency_ms=1000,
            context_limit=4096,
            task_success=False,
            tool_call_accuracy=0.5,
            retrieval_precision=0.0,
            groundedness_score=0.2,
            cost_usd=0.40,
        ),
    ]

    metrics = aggregate_eval_metrics(results)

    assert metrics.task_success_rate == pytest.approx(2 / 4)
    assert metrics.tool_call_accuracy == pytest.approx((1.0 + 0.0 + 0.5) / 3)
    assert metrics.retrieval_precision == pytest.approx(((2 / 3) + 0.5 + 0.0) / 3)
    assert metrics.groundedness_score == pytest.approx((0.9 + 0.4 + 0.8 + 0.2) / 4)
    assert metrics.hallucination_rate == pytest.approx((0.1 + 0.6 + 0.2 + 0.8) / 4)
    assert metrics.cost_per_successful_task == pytest.approx(1.00 / 2)
    assert metrics.cost_per_attempted_task == pytest.approx(1.00 / 4)
    assert metrics.latency_p50_ms == pytest.approx(250)
    assert metrics.latency_p95_ms == pytest.approx(895)


def test_aggregate_eval_metrics_handles_no_successful_tasks_without_dividing_by_zero():
    results = [
        compute_metrics(
            judge_score=0.0,
            prompt_tokens=10,
            completion_tokens=10,
            latency_ms=120,
            context_limit=4096,
            task_success=False,
            groundedness_score=0.0,
            cost_usd=0.25,
        )
    ]

    metrics = aggregate_eval_metrics(results)

    assert metrics.task_success_rate == 0.0
    assert metrics.cost_per_successful_task is None
    assert metrics.latency_p50_ms == pytest.approx(120)
    assert metrics.latency_p95_ms == pytest.approx(120)


def test_aggregate_eval_metrics_returns_empty_summary_for_empty_result_sets():
    metrics = aggregate_eval_metrics([])

    assert metrics.task_success_rate is None
    assert metrics.tool_call_accuracy is None
    assert metrics.retrieval_precision is None
    assert metrics.groundedness_score is None
    assert metrics.hallucination_rate is None
    assert metrics.cost_per_successful_task is None
    assert metrics.cost_per_attempted_task is None
    assert metrics.latency_p50_ms is None
    assert metrics.latency_p95_ms is None


def test_metric_scorers_convert_task_artifacts_into_case_level_scores():
    assert score_tool_call_accuracy(
        expected_tools=["search", "summarize"],
        actual_tool_calls=[{"name": "search"}, {"tool": "summarize"}],
    ) == pytest.approx(1.0)
    assert score_tool_call_accuracy(
        expected_tools=["search", "summarize"],
        actual_tool_calls=[{"name": "search"}],
    ) == pytest.approx(0.0)

    assert score_retrieval_precision(
        relevant_doc_ids=["doc-a", "doc-c"],
        retrieved_docs=[{"id": "doc-a"}, {"doc_id": "doc-b"}, "doc-c"],
    ) == pytest.approx(2 / 3)

    assert score_groundedness(
        judge_score=0.1,
        judge_criteria={"faithfulness": 0.75},
        expected_claims=None,
        output="",
    ) == pytest.approx(0.75)
