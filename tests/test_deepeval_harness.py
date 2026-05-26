import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from promptops.core.adapters.base import ModelResponse
from promptops.eval.deepeval_harness import PromptOpsDeepEvalLLM


def _mock_adapter(output: str) -> MagicMock:
    adapter = MagicMock()
    resp = ModelResponse(output=output, prompt_tokens=5, completion_tokens=10)
    adapter.generate = AsyncMock(return_value=resp)
    return adapter


def test_a_generate_routes_through_adapter():
    adapter = _mock_adapter("bridge response")
    bridge = PromptOpsDeepEvalLLM(adapter=adapter, model="llama3.1")

    result = asyncio.run(bridge.a_generate("hello"))

    adapter.generate.assert_called_once_with(
        model="llama3.1",
        system="",
        prompt="hello",
        params={"temperature": 0.0, "max_tokens": 1000},
    )
    assert result == "bridge response"


def test_generate_sync_wrapper_returns_output():
    adapter = _mock_adapter("sync response")
    bridge = PromptOpsDeepEvalLLM(adapter=adapter, model="llama3.1")

    result = bridge.generate("sync prompt")

    assert result == "sync response"


def test_get_model_name():
    adapter = MagicMock()
    bridge = PromptOpsDeepEvalLLM(adapter=adapter, model="llama3.1")
    assert bridge.get_model_name() == "llama3.1"


from unittest.mock import patch
from promptops.eval.deepeval_harness import DeepEvalHarness
from promptops.eval.judge import JudgeResult
from deepeval.test_case import LLMTestCaseParams


def _make_mock_metric(name: str, score: float, reason: str) -> MagicMock:
    m = MagicMock()
    m.name = name
    m.score = score
    m.reason = reason
    m.a_measure = AsyncMock()
    return m


def test_deepeval_harness_returns_judge_result():
    adapter = _mock_adapter("")

    with patch("promptops.eval.deepeval_harness.GEval") as MockGEval, \
         patch("promptops.eval.deepeval_harness.AnswerRelevancyMetric") as MockAR:

        mock_geval = _make_mock_metric("Quality", 0.8, "factually correct")
        mock_ar = _make_mock_metric("AnswerRelevancy", 0.6, "relevant")
        MockGEval.return_value = mock_geval
        MockAR.return_value = mock_ar

        harness = DeepEvalHarness(adapter=adapter, model="llama3.1")
        result = asyncio.run(
            harness.evaluate(
                user_input={"input": "test"},
                actual_output="test output",
                expected_output=None,
                rubric=None,
            )
        )

    assert isinstance(result, JudgeResult)
    assert result.score == pytest.approx(0.7)   # (0.8 + 0.6) / 2
    assert result.criteria["Quality"] == pytest.approx(0.8)
    assert result.criteria["AnswerRelevancy"] == pytest.approx(0.6)
    assert "Quality" in result.reasoning
    assert "AnswerRelevancy" in result.reasoning


def test_deepeval_harness_excludes_expected_output_param_when_none():
    adapter = _mock_adapter("")

    with patch("promptops.eval.deepeval_harness.GEval") as MockGEval, \
         patch("promptops.eval.deepeval_harness.AnswerRelevancyMetric") as MockAR:

        mock_geval = _make_mock_metric("Quality", 0.7, "ok")
        mock_ar = _make_mock_metric("AnswerRelevancy", 0.7, "ok")
        MockGEval.return_value = mock_geval
        MockAR.return_value = mock_ar

        harness = DeepEvalHarness(adapter=adapter, model="llama3.1")
        asyncio.run(
            harness.evaluate(
                user_input={"input": "x"},
                actual_output="y",
                expected_output=None,
                rubric=None,
            )
        )

    call_kwargs = MockGEval.call_args.kwargs
    assert LLMTestCaseParams.EXPECTED_OUTPUT not in call_kwargs["evaluation_params"]


def test_deepeval_harness_includes_expected_output_param_when_provided():
    adapter = _mock_adapter("")

    with patch("promptops.eval.deepeval_harness.GEval") as MockGEval, \
         patch("promptops.eval.deepeval_harness.AnswerRelevancyMetric") as MockAR:

        mock_geval = _make_mock_metric("Quality", 0.9, "ok")
        mock_ar = _make_mock_metric("AnswerRelevancy", 0.9, "ok")
        MockGEval.return_value = mock_geval
        MockAR.return_value = mock_ar

        harness = DeepEvalHarness(adapter=adapter, model="llama3.1")
        asyncio.run(
            harness.evaluate(
                user_input={"input": "x"},
                actual_output="y",
                expected_output="expected answer",
                rubric=None,
            )
        )

    call_kwargs = MockGEval.call_args.kwargs
    assert LLMTestCaseParams.EXPECTED_OUTPUT in call_kwargs["evaluation_params"]
