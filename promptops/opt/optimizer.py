from __future__ import annotations

import asyncio
from typing import Any

from promptops.core.prompt import Prompt
from promptops.core.adapters.base import BaseAdapter
from promptops.core.runner import run_dataset
from promptops.tests.testcase import TestCase
from promptops.opt.mutations import basic_mutations
from promptops.opt.rewriter import rewrite_prompt


async def optimize_prompt(
    adapter: BaseAdapter,
    base_prompt: Prompt,
    testcases: list[TestCase],
    judge_model: str,
    iterations: int = 2,
    use_rewriter: bool = True,
    rewriter_model: str | None = None,
    min_delta: float = 0.005,
) -> dict[str, Any]:
    best_prompt = base_prompt
    best_result = await run_dataset(adapter, best_prompt, testcases, judge_model)
    prev_best_objective = best_result["avg_objective"]

    for _ in range(iterations):
        candidates = list(basic_mutations(best_prompt, testcases=testcases))
        if use_rewriter:
            rw_model = rewriter_model or judge_model
            # Pass current score + sample reasoning to the rewriter
            sample_reasoning = None
            rewritten = await rewrite_prompt(
                adapter,
                rw_model,
                best_prompt,
                current_score=best_result.get("avg_judge_score"),
                judge_reasoning=sample_reasoning,
            )
            if rewritten is not None:
                candidates.append(rewritten)

        # Evaluate all candidates in parallel
        cand_results = await asyncio.gather(
            *[run_dataset(adapter, cand, testcases, judge_model) for cand in candidates]
        )

        for cand, result in zip(candidates, cand_results):
            if result["avg_objective"] > best_result["avg_objective"]:
                best_result = result
                best_prompt = cand

        # Early stopping: if improvement is below min_delta, stop
        current_objective = best_result["avg_objective"]
        if current_objective - prev_best_objective < min_delta:
            break
        prev_best_objective = current_objective

    return {
        "best_prompt": best_prompt,
        "best_result": best_result,
    }
