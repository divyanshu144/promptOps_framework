import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from promptops.core.prompt import Prompt
from promptops.opt.optimizer import optimize_prompt
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


def _result(objective: float, judge_score: float, pass_rate: float) -> dict:
    return {
        "run_id": 1,
        "avg_objective": objective,
        "avg_judge_score": judge_score,
        "pass_rate": pass_rate,
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
