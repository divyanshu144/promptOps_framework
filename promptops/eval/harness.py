from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

from promptops.eval.judge import JudgeResult


class EvalHarness(ABC):
    @abstractmethod
    async def evaluate(
        self,
        user_input: Dict[str, Any],
        actual_output: str,
        expected_output: str | None,
        rubric: Dict[str, Any] | None,
    ) -> JudgeResult:
        ...
