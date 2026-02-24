from __future__ import annotations

from typing import Any

from promptops.core.prompt import Prompt
from promptops.core.adapter import OllamaAdapter
from promptops.core.runner import run_dataset
from promptops.tests.testcase import TestCase
from promptops.opt.mutations import basic_mutations
from promptops.opt.rewriter import rewrite_prompt


async def optimize_prompt(
    adapter: OllamaAdapter,
    base_prompt: Prompt,
    testcases: list[TestCase],
    judge_model: str,
    iterations: int = 2,
    use_rewriter: bool = True,
    rewriter_model: str | None = None,
) -> dict[str, Any]:
    best_prompt = base_prompt
    best_result = await run_dataset(adapter, best_prompt, testcases, judge_model)

    for _ in range(iterations):
        candidates = list(basic_mutations(best_prompt))
        if use_rewriter:
            rw_model = rewriter_model or judge_model
            rewritten = await rewrite_prompt(adapter, rw_model, best_prompt)
            if rewritten is not None:
                candidates.append(rewritten)
        for cand in candidates:
            result = await run_dataset(adapter, cand, testcases, judge_model)
            if result["avg_objective"] > best_result["avg_objective"]:
                best_result = result
                best_prompt = cand

    return {
        "best_prompt": best_prompt,
        "best_result": best_result,
    }
