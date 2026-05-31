import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from promptops.core.adapters.base import ModelResponse
from promptops.core.prompt import Prompt
from promptops.core.runner import run_prompt, run_dataset
from promptops.eval.judge import JudgeResult
from promptops.tests.testcase import TestCase


def _mock_adapter(output: str = "response") -> MagicMock:
    adapter = MagicMock()
    resp = ModelResponse(output=output, prompt_tokens=10, completion_tokens=20)
    adapter.generate = AsyncMock(return_value=resp)
    adapter.health_check = AsyncMock(return_value=True)
    return adapter


def _default_prompt() -> Prompt:
    return Prompt(
        name="test",
        system="You are helpful.",
        template="{input}",
        model="llama3.1",
        params={"temperature": 0.2, "max_tokens": 200},
        context_limit=4096,
        provider="ollama",
    )


def _default_testcase() -> TestCase:
    return TestCase(input={"input": "hello"}, expected=None, rubric={"quality": 1.0})


def test_run_prompt_uses_provided_harness():
    adapter = _mock_adapter()
    prompt = _default_prompt()
    tc = _default_testcase()

    mock_harness = MagicMock()
    mock_harness.evaluate = AsyncMock(
        return_value=JudgeResult(score=0.9, criteria={"quality": 0.9}, reasoning="great")
    )

    output, metrics, judge_info = asyncio.run(
        run_prompt(adapter, prompt, tc, judge_model="llama3.1", harness=mock_harness)
    )

    mock_harness.evaluate.assert_called_once_with(
        user_input={"input": "hello"},
        actual_output="response",
        expected_output=None,
        rubric={"quality": 1.0},
    )
    assert judge_info["judge_score"] == pytest.approx(0.9)
    assert judge_info["passed"] is True


def test_run_prompt_marks_failed_when_below_threshold():
    adapter = _mock_adapter()
    prompt = _default_prompt()
    tc = TestCase(input={"input": "hello"}, rubric={"quality": 1.0}, threshold=0.8)

    mock_harness = MagicMock()
    mock_harness.evaluate = AsyncMock(
        return_value=JudgeResult(score=0.7, criteria={"quality": 0.7}, reasoning="ok")
    )

    _output, _metrics, judge_info = asyncio.run(
        run_prompt(adapter, prompt, tc, judge_model="llama3.1", harness=mock_harness)
    )

    assert judge_info["passed"] is False


def test_run_prompt_defaults_to_llm_judge_harness_when_none():
    adapter = _mock_adapter()
    prompt = _default_prompt()
    tc = _default_testcase()

    judge_result = JudgeResult(score=0.7, criteria={}, reasoning="ok")

    with patch("promptops.core.runner.LLMJudgeHarness") as MockHarness:
        mock_instance = MagicMock()
        mock_instance.evaluate = AsyncMock(return_value=judge_result)
        MockHarness.return_value = mock_instance

        asyncio.run(run_prompt(adapter, prompt, tc, judge_model="llama3.1", harness=None))

    MockHarness.assert_called_once_with(adapter, "llama3.1")


def test_run_dataset_passes_harness_to_run_prompt():
    adapter = _mock_adapter()
    prompt = _default_prompt()
    tcs = [
        TestCase(input={"input": "pass"}, rubric={"quality": 1.0}, threshold=0.7),
        TestCase(input={"input": "fail"}, rubric={"quality": 1.0}, threshold=0.7),
    ]

    mock_harness = MagicMock()
    mock_harness.evaluate = AsyncMock(
        side_effect=[
            JudgeResult(score=0.8, criteria={}, reasoning="good"),
            JudgeResult(score=0.6, criteria={}, reasoning="weak"),
        ]
    )

    mock_run_info = MagicMock()
    mock_run_info.info.run_id = "test-run-id"
    mock_ctx = MagicMock()
    mock_ctx.__enter__ = MagicMock(return_value=mock_run_info)
    mock_ctx.__exit__ = MagicMock(return_value=False)

    with patch("promptops.core.runner.init_db"), \
         patch("promptops.core.runner.mlflow") as mock_mlflow, \
         patch("promptops.core.runner.insert_run", return_value=1) as mock_insert_run, \
         patch("promptops.core.runner.insert_run_result") as mock_insert_result, \
         patch("promptops.core.runner.get_best_for_prompt", return_value=None):
        mock_mlflow.active_run.return_value = None
        mock_mlflow.start_run.return_value = mock_ctx
        result = asyncio.run(
            run_dataset(adapter, prompt, tcs, judge_model="llama3.1", harness=mock_harness)
        )

    assert mock_harness.evaluate.call_count == 2
    assert result["avg_judge_score"] == pytest.approx(0.7)
    assert result["pass_rate"] == pytest.approx(0.5)
    assert mock_insert_run.call_args.args[0]["pass_rate"] == pytest.approx(0.5)
    passed_values = [call.kwargs["passed"] for call in mock_insert_result.call_args_list]
    assert passed_values == [True, False]
