import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from promptops.eval.harness import EvalHarness
from promptops.eval.llm_judge_harness import LLMJudgeHarness
from promptops.eval.judge import JudgeResult
from promptops.core.adapters.base import ModelResponse


def test_eval_harness_is_abstract():
    with pytest.raises(TypeError):
        EvalHarness()


def test_eval_harness_has_evaluate_method():
    assert hasattr(EvalHarness, "evaluate")


def _mock_adapter(output: str) -> MagicMock:
    adapter = MagicMock()
    resp = ModelResponse(output=output, prompt_tokens=5, completion_tokens=10)
    adapter.generate = AsyncMock(return_value=resp)
    return adapter


def test_llm_judge_harness_delegates_to_judge_output():
    adapter = _mock_adapter("")
    harness = LLMJudgeHarness(adapter=adapter, model="llama3.1")
    expected = JudgeResult(score=0.8, criteria={"quality": 0.8}, reasoning="good")

    with patch("promptops.eval.llm_judge_harness.judge_output", return_value=expected) as mock_judge:
        result = asyncio.run(
            harness.evaluate(
                user_input={"input": "test"},
                actual_output="test output",
                expected_output=None,
                rubric={"quality": 1.0},
            )
        )

    mock_judge.assert_called_once_with(
        adapter=adapter,
        model="llama3.1",
        rubric={"quality": 1.0},
        user_input={"input": "test"},
        assistant_output="test output",
        expected=None,
    )
    assert result.score == 0.8


def test_llm_judge_harness_uses_default_rubric_when_none():
    adapter = _mock_adapter("")
    harness = LLMJudgeHarness(adapter=adapter, model="llama3.1")
    expected = JudgeResult(score=0.5, criteria={}, reasoning=None)

    with patch("promptops.eval.llm_judge_harness.judge_output", return_value=expected) as mock_judge:
        asyncio.run(
            harness.evaluate(
                user_input={"input": "x"},
                actual_output="y",
                expected_output=None,
                rubric=None,
            )
        )

    call_kwargs = mock_judge.call_args.kwargs
    assert call_kwargs["rubric"] == {"quality": 1.0}
