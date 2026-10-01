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

    async def a_generate(self, prompt: str, *args: Any, **kwargs: Any) -> str:
        schema = kwargs.get("schema")
        system = ""
        params: dict[str, Any] = {"temperature": 0.0, "max_tokens": 1000}
        if schema is not None:
            system = (
                "You are an evaluation model. Return only valid JSON. Do not return "
                "markdown, code fences, or Python code."
            )
            prompt = (
                f"{prompt}\n\nReturn only a JSON object that matches this schema:\n"
                f"{schema}\nNo markdown. No code fences. No explanation."
            )
            params["format"] = "json"

        resp = await self._adapter.generate(
            model=self._model,
            system=system,
            prompt=prompt,
            params=params,
        )
        return _strip_json_markdown(resp.output)

    def generate(self, prompt: str, *args: Any, **kwargs: Any) -> str:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, self.a_generate(prompt, *args, **kwargs)).result()


def _strip_json_markdown(output: str) -> str:
    text = output.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


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

        scores = {_metric_name(m): float(m.score) for m in metrics}
        avg = sum(scores.values()) / len(scores)
        reasoning = "; ".join(
            f"{_metric_name(m)}: {getattr(m, 'reason', '')}" for m in metrics
        )
        return JudgeResult(score=avg, criteria=scores, reasoning=reasoning)


def _metric_name(metric: Any) -> str:
    name = getattr(metric, "name", None)
    if isinstance(name, str) and name:
        return name
    return metric.__class__.__name__
