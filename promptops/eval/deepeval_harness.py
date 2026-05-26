from __future__ import annotations

import asyncio
import json
from typing import Any, Dict

from deepeval.metrics import AnswerRelevancyMetric, GEval
from deepeval.models.base_model import DeepEvalBaseLLM
from deepeval.test_case import LLMTestCase, LLMTestCaseParams

from promptops.core.adapters.base import BaseAdapter
from promptops.eval.harness import EvalHarness
from promptops.eval.judge import JudgeResult


class PromptOpsDeepEvalLLM(DeepEvalBaseLLM):
    def __init__(self, adapter: BaseAdapter, model: str) -> None:
        self._adapter = adapter
        self._model = model

    def load_model(self, *args: Any, **kwargs: Any) -> PromptOpsDeepEvalLLM:
        return self

    def get_model_name(self) -> str:
        return self._model

    async def a_generate(self, prompt: str) -> str:
        resp = await self._adapter.generate(
            model=self._model,
            system="",
            prompt=prompt,
            params={"temperature": 0.0, "max_tokens": 1000},
        )
        return resp.output

    def generate(self, prompt: str) -> str:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, self.a_generate(prompt)).result()


class DeepEvalHarness(EvalHarness):
    def __init__(self, adapter: BaseAdapter, model: str) -> None:
        self._llm = PromptOpsDeepEvalLLM(adapter, model)

    async def evaluate(
        self,
        user_input: Dict[str, Any],
        actual_output: str,
        expected_output: str | None,
        rubric: Dict[str, Any] | None,  # not forwarded — DeepEval uses fixed GEval criteria
    ) -> JudgeResult:
        eval_params = [LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT]
        if expected_output is not None:
            eval_params.append(LLMTestCaseParams.EXPECTED_OUTPUT)

        metrics = [
            GEval(
                name="Quality",
                criteria="Is the output factually correct, coherent, and directly addresses the input?",
                evaluation_params=eval_params,
                model=self._llm,
                threshold=0.5,
            ),
            AnswerRelevancyMetric(model=self._llm, threshold=0.5),
        ]

        test_case = LLMTestCase(
            input=json.dumps(user_input),
            actual_output=actual_output,
            expected_output=expected_output,
        )
        await asyncio.gather(*[m.a_measure(test_case) for m in metrics])

        scores = {m.name: float(m.score) for m in metrics}
        avg = sum(scores.values()) / len(scores)
        reasoning = "; ".join(
            f"{m.name}: {getattr(m, 'reason', '')}" for m in metrics
        )
        return JudgeResult(score=avg, criteria=scores, reasoning=reasoning)
