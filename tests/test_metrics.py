import pytest
from promptops.eval.metrics import compute_metrics


def test_basic_objective_is_penalized():
    m = compute_metrics(
        judge_score=0.8,
        prompt_tokens=100,
        completion_tokens=50,
        latency_ms=500.0,
        context_limit=4096,
        format_valid=None,
    )
    assert m.judge_score == 0.8
    assert m.total_tokens == 150
    assert m.format_penalty == 0.0
    assert m.objective < 0.8  # penalties push it below raw score


def test_format_penalty_applied_when_invalid():
    m = compute_metrics(
        judge_score=0.9,
        prompt_tokens=10,
        completion_tokens=10,
        latency_ms=0.0,
        context_limit=4096,
        format_valid=False,
    )
    assert m.format_penalty == 0.2
    assert m.objective < 0.9 - 0.2 + 0.001  # at most judge - format_penalty


def test_no_format_penalty_when_valid():
    m = compute_metrics(
        judge_score=0.9,
        prompt_tokens=10,
        completion_tokens=10,
        latency_ms=0.0,
        context_limit=4096,
        format_valid=True,
    )
    assert m.format_penalty == 0.0


def test_none_tokens_zero_penalty():
    m = compute_metrics(
        judge_score=0.5,
        prompt_tokens=None,
        completion_tokens=None,
        latency_ms=None,
        context_limit=4096,
        format_valid=None,
    )
    assert m.total_tokens is None
    assert m.token_penalty == 0.0
    assert m.context_window_used is None
    assert m.objective == pytest.approx(0.5)


def test_latency_penalty():
    m_fast = compute_metrics(0.8, None, None, 0.0, 4096)
    m_slow = compute_metrics(0.8, None, None, 10000.0, 4096)
    assert m_slow.objective < m_fast.objective


def test_token_penalty_proportional_to_context():
    m_small = compute_metrics(0.8, 100, 100, 0.0, 4096)
    m_large = compute_metrics(0.8, 2000, 2000, 0.0, 4096)
    assert m_large.objective < m_small.objective
