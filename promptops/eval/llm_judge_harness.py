from __future__ import annotations

from typing import Any, Dict

from promptops.core.adapters.base import BaseAdapter
from promptops.eval.harness import EvalHarness
from promptops.eval.judge import JudgeResult, judge_output


class LLMJudgeHarness(EvalHarness):
    def __init__(self, adapter: BaseAdapter, model: str) -> None:
        self._adapter = adapter
        self._model = model

    async def evaluate(
        self,
        user_input: Dict[str, Any],
        actual_output: str,
        expected_output: str | None,
        rubric: Dict[str, Any] | None,
    ) -> JudgeResult:
        return await judge_output(
            adapter=self._adapter,
            model=self._model,
            rubric=rubric or {"quality": 1.0},
            user_input=user_input,
            assistant_output=actual_output,
            expected=expected_output,
        )
