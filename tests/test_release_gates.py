import pytest

from promptops.eval.metrics import AggregateEvalMetrics
from promptops.eval.release import ReleaseGateThresholds, evaluate_release_gate


def _metrics(**overrides):
    values = {
        "task_success_rate": 0.92,
        "tool_call_accuracy": 0.95,
        "retrieval_precision": 0.80,
        "groundedness_score": 0.88,
        "hallucination_rate": 0.04,
        "cost_per_successful_task": 0.12,
        "latency_p50_ms": 450.0,
        "latency_p95_ms": 1100.0,
    }
    values.update(overrides)
    return AggregateEvalMetrics(**values)


def test_release_gates_pass_when_all_metric_thresholds_are_satisfied():
    thresholds = ReleaseGateThresholds(
        minimums={
            "task_success_rate": 0.90,
            "tool_call_accuracy": 0.90,
            "retrieval_precision": 0.75,
            "groundedness_score": 0.85,
        },
        maximums={
            "hallucination_rate": 0.05,
            "cost_per_successful_task": 0.15,
            "latency_p50_ms": 500,
            "latency_p95_ms": 1200,
        },
    )

    decision = evaluate_release_gate(_metrics(), thresholds)

    assert decision.passed is True
    assert decision.failures == []
    assert decision.metrics["task_success_rate"] == pytest.approx(0.92)
    assert decision.metrics["latency_p95_ms"] == pytest.approx(1100.0)


def test_release_gates_fail_closed_and_report_each_failed_threshold():
    thresholds = ReleaseGateThresholds(
        minimums={"task_success_rate": 0.90},
        maximums={
            "hallucination_rate": 0.05,
            "cost_per_successful_task": 0.15,
            "latency_p95_ms": 1200,
        },
    )

    decision = evaluate_release_gate(
        _metrics(
            task_success_rate=0.89,
            hallucination_rate=0.06,
            cost_per_successful_task=None,
            latency_p95_ms=1300,
        ),
        thresholds,
    )

    assert decision.passed is False
    assert decision.failures == [
        "task_success_rate 0.89 < minimum 0.9",
        "hallucination_rate 0.06 > maximum 0.05",
        "cost_per_successful_task missing; required <= 0.15",
        "latency_p95_ms 1300 > maximum 1200",
    ]


def test_release_gates_fail_closed_when_required_metric_is_missing():
    decision = evaluate_release_gate(
        _metrics(),
        ReleaseGateThresholds(minimums={"unknown_metric": 0.5}),
    )

    assert decision.passed is False
    assert decision.failures == ["unknown_metric missing; required >= 0.5"]


def test_release_gates_can_fail_on_regressions_from_baseline():
    thresholds = ReleaseGateThresholds(
        max_regression={
            "task_success_rate": 0.02,
            "groundedness_score": 0.03,
        }
    )

    decision = evaluate_release_gate(
        _metrics(task_success_rate=0.92, groundedness_score=0.86),
        thresholds,
        baseline_metrics=_metrics(task_success_rate=0.95, groundedness_score=0.90),
    )

    assert decision.passed is False
    assert decision.failures == [
        "task_success_rate regressed by 0.03; allowed drop 0.02",
        "groundedness_score regressed by 0.04; allowed drop 0.03",
    ]
    assert decision.baseline_metrics["task_success_rate"] == pytest.approx(0.95)
