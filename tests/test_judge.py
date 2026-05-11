import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from promptops.eval.judge import judge_output, _single_judge_call
from promptops.core.adapters.base import ModelResponse


def _adapter(output: str) -> MagicMock:
    adapter = MagicMock()
    resp = ModelResponse(output=output, prompt_tokens=10, completion_tokens=20)
    adapter.generate = AsyncMock(return_value=resp)
    return adapter


def test_parses_valid_json():
    adapter = _adapter('{"criteria": {"quality": 0.8}, "overall": 0.8, "reasoning": "Good"}')
    result = asyncio.run(
        judge_output(adapter, "model", {"quality": 1.0}, {"input": "hi"}, "some output")
    )
    assert abs(result.score - 0.8) < 0.01
    assert "quality" in result.criteria
    assert result.reasoning == "Good"


def test_parses_json_with_text_preamble():
    adapter = _adapter(
        'Here is my evaluation:\n{"criteria": {"accuracy": 0.9}, "overall": 0.9, "reasoning": "ok"}'
    )
    result = asyncio.run(
        _single_judge_call(adapter, "m", {"accuracy": 1.0}, {"input": "x"}, "y")
    )
    assert abs(result.score - 0.9) < 0.01


def test_fallback_regex_extracts_score():
    adapter = _adapter("I would rate this 0.6 overall.")
    result = asyncio.run(
        _single_judge_call(adapter, "m", {"quality": 1.0}, {"input": "x"}, "y")
    )
    assert result.score == pytest.approx(0.6)


def test_fallback_returns_zero_on_no_match():
    adapter = _adapter("This response is unacceptable and has no numeric rating.")
    result = asyncio.run(
        _single_judge_call(adapter, "m", {"quality": 1.0}, {"input": "x"}, "y")
    )
    assert result.score == 0.0


def test_judge_averages_three_calls():
    adapter = MagicMock()
    adapter.generate = AsyncMock(
        side_effect=[
            ModelResponse(output='{"criteria": {}, "overall": 0.6, "reasoning": "r"}', prompt_tokens=5, completion_tokens=5),
            ModelResponse(output='{"criteria": {}, "overall": 0.8, "reasoning": "r"}', prompt_tokens=5, completion_tokens=5),
            ModelResponse(output='{"criteria": {}, "overall": 1.0, "reasoning": "r"}', prompt_tokens=5, completion_tokens=5),
        ]
    )
    result = asyncio.run(
        judge_output(adapter, "m", {"quality": 1.0}, {"input": "x"}, "y")
    )
    assert abs(result.score - 0.8) < 0.01  # (0.6 + 0.8 + 1.0) / 3


def test_judge_with_expected_output():
    adapter = _adapter('{"criteria": {"factuality": 0.9}, "overall": 0.9, "reasoning": "Matches expected"}')
    result = asyncio.run(
        judge_output(
            adapter, "m", {"factuality": 1.0}, {"input": "x"}, "y", expected="the expected answer"
        )
    )
    assert result.score > 0
    # Verify expected was passed into the prompt
    call_args = adapter.generate.call_args_list[0]
    prompt_text = call_args.kwargs.get("prompt") or (call_args.args[2] if len(call_args.args) > 2 else "")
    assert "the expected answer" in prompt_text
