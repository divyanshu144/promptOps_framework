import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from promptops.core.prompt import Prompt
from promptops.opt.optimizer import optimize_prompt, _significant_improvement
from promptops.tests.testcase import TestCase


def _prompt(name: str = "base") -> Prompt:
    return Prompt(
        name=name,
        system="You are helpful.",
        template="{input}",
        model="llama3.1",
        params={"temperature": 0.2, "max_tokens": 200},
        provider="ollama",
    )


def _result(
    objective: float,
    judge_score: float,
    pass_rate: float,
    run_id: int = 1,
    aggregate_metrics: dict | None = None,
) -> dict:
    return {
        "run_id": run_id,
        "avg_objective": objective,
        "avg_judge_score": judge_score,
        "pass_rate": pass_rate,
        "aggregate_metrics": aggregate_metrics or {"latency_p50_ms": 100.0},
        "outputs": ["output"],
        "regression": False,
        "regression_warning": None,
    }


def test_optimize_prompt_returns_baseline_and_pass_rate_comparison():
    adapter = MagicMock()
    base = _prompt("base")
    candidate = _prompt("base_concise")
    testcases = [TestCase(input={"input": "hello"}, threshold=0.7)]

    with patch("promptops.opt.optimizer.basic_mutations", return_value=[candidate]), patch(
        "promptops.opt.optimizer.run_dataset",
        new=AsyncMock(
            side_effect=[
                _result(objective=0.50, judge_score=0.60, pass_rate=0.50),
                _result(objective=0.80, judge_score=0.90, pass_rate=1.00),
            ]
        ),
    ):
        result = asyncio.run(
            optimize_prompt(
                adapter=adapter,
                base_prompt=base,
                testcases=testcases,
                judge_model="llama3.1",
                iterations=1,
                use_rewriter=False,
            )
        )

    assert result["baseline_result"]["pass_rate"] == pytest.approx(0.50)
    assert result["best_result"]["pass_rate"] == pytest.approx(1.00)
    assert result["comparison"]["pass_rate_delta"] == pytest.approx(0.50)
    assert result["comparison"]["objective_delta"] == pytest.approx(0.30)
    assert result["comparison"]["judge_score_delta"] == pytest.approx(0.30)
    assert result["comparison"]["improved"] is True
    assert result["comparison"]["baseline_prompt_name"] == "base"
    assert result["comparison"]["best_prompt_name"] == "base_concise"


def test_optimize_prompt_averages_repeats():
    adapter = MagicMock()
    base = _prompt("base")
    candidate = _prompt("base_concise")
    testcases = [TestCase(input={"input": "hello"}, threshold=0.7)]

    run_dataset_mock = AsyncMock(
        side_effect=[
            # baseline: 3 repeats
            _result(objective=0.40, judge_score=0.50, pass_rate=0.0, run_id=1),
            _result(objective=0.50, judge_score=0.60, pass_rate=0.5, run_id=2),
            _result(objective=0.60, judge_score=0.70, pass_rate=1.0, run_id=3),
            # candidate: 3 repeats
            _result(objective=0.70, judge_score=0.80, pass_rate=1.0, run_id=4),
            _result(objective=0.80, judge_score=0.90, pass_rate=1.0, run_id=5),
            _result(objective=0.90, judge_score=1.00, pass_rate=1.0, run_id=6),
        ]
    )

    with patch("promptops.opt.optimizer.basic_mutations", return_value=[candidate]), patch(
        "promptops.opt.optimizer.run_dataset", new=run_dataset_mock
    ):
        result = asyncio.run(
            optimize_prompt(
                adapter=adapter,
                base_prompt=base,
                testcases=testcases,
                judge_model="llama3.1",
                iterations=1,
                use_rewriter=False,
                repeats=3,
            )
        )

    assert run_dataset_mock.await_count == 6
    assert result["baseline_result"]["avg_objective"] == pytest.approx(0.50)
    assert result["baseline_result"]["objective_runs"] == [0.40, 0.50, 0.60]
    assert result["baseline_result"]["run_ids"] == [1, 2, 3]
    assert result["best_result"]["avg_objective"] == pytest.approx(0.80)
    assert result["best_result"]["run_ids"] == [4, 5, 6]
    assert result["best_result"]["aggregate_metrics"]["latency_p50_ms"] == pytest.approx(100.0)
    assert result["comparison"]["objective_delta"] == pytest.approx(0.30)
    assert result["comparison"]["best_prompt_name"] == "base_concise"
    assert result["comparison"]["significant_improvement"] is True


def test_significant_improvement_rejects_high_variance_win():
    baseline = {"avg_objective": 0.50, "objective_runs": [0.40, 0.50, 0.60]}
    candidate = {"avg_objective": 0.6333, "objective_runs": [0.30, 0.90, 0.70]}

    # Plain mean comparison would call this an improvement...
    assert candidate["avg_objective"] > baseline["avg_objective"]
    # ...but the significance gate doesn't, given the candidate's high variance relative
    # to the size of the mean difference.
    assert _significant_improvement(baseline, candidate) is False


def test_significant_improvement_accepts_clear_win():
    baseline = {"avg_objective": 0.50, "objective_runs": [0.48, 0.50, 0.52]}
    candidate = {"avg_objective": 0.80, "objective_runs": [0.78, 0.80, 0.82]}
    assert _significant_improvement(baseline, candidate) is True


def test_significant_improvement_falls_back_to_mean_without_repeat_data():
    """With fewer than 2 runs per side (e.g. repeats=1), there's no variance to estimate,
    so the gate falls back to a plain mean comparison instead of always rejecting."""
    baseline = {"avg_objective": 0.50}
    candidate = {"avg_objective": 0.51}
    assert _significant_improvement(baseline, candidate) is True


def test_optimize_prompt_significance_gate_rejects_noisy_improvement():
    """A candidate with a higher mean objective but wide spread should not become "best"
    if the difference from baseline is within the observed noise band — end to end
    through optimize_prompt(), not just the helper directly."""
    adapter = MagicMock()
    base = _prompt("base")
    candidate = _prompt("base_noisy")
    testcases = [TestCase(input={"input": "hello"}, threshold=0.7)]

    run_dataset_mock = AsyncMock(
        side_effect=[
            # baseline: tight spread around 0.50
            _result(objective=0.40, judge_score=0.50, pass_rate=0.5, run_id=1),
            _result(objective=0.50, judge_score=0.60, pass_rate=0.5, run_id=2),
            _result(objective=0.60, judge_score=0.70, pass_rate=0.5, run_id=3),
            # candidate: higher mean (0.633) but wide spread -> not a significant win
            _result(objective=0.30, judge_score=0.40, pass_rate=0.5, run_id=4),
            _result(objective=0.90, judge_score=1.00, pass_rate=1.0, run_id=5),
            _result(objective=0.70, judge_score=0.80, pass_rate=1.0, run_id=6),
        ]
    )

    with patch("promptops.opt.optimizer.basic_mutations", return_value=[candidate]), patch(
        "promptops.opt.optimizer.run_dataset", new=run_dataset_mock
    ):
        result = asyncio.run(
            optimize_prompt(
                adapter=adapter,
                base_prompt=base,
                testcases=testcases,
                judge_model="llama3.1",
                iterations=1,
                use_rewriter=False,
                repeats=3,
            )
        )

    # The gate keeps the baseline as "best" since the candidate's win is within the noise band.
    assert result["comparison"]["best_prompt_name"] == "base"
    assert result["comparison"]["improved"] is False
    assert result["comparison"]["significant_improvement"] is False


def test_optimize_prompt_repeats_default_unchanged():
    """repeats defaults to 1 — single run_dataset call per candidate, no averaging wrapper."""
    adapter = MagicMock()
    base = _prompt("base")
    testcases = [TestCase(input={"input": "hello"}, threshold=0.7)]

    run_dataset_mock = AsyncMock(
        side_effect=[_result(objective=0.50, judge_score=0.60, pass_rate=0.50)]
    )

    with patch("promptops.opt.optimizer.basic_mutations", return_value=[]), patch(
        "promptops.opt.optimizer.run_dataset", new=run_dataset_mock
    ):
        result = asyncio.run(
            optimize_prompt(
                adapter=adapter,
                base_prompt=base,
                testcases=testcases,
                judge_model="llama3.1",
                iterations=1,
                use_rewriter=False,
            )
        )

    assert run_dataset_mock.await_count == 1
    assert "run_ids" not in result["baseline_result"]
    assert result["baseline_result"]["avg_objective"] == pytest.approx(0.50)
