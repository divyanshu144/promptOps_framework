from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable

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
    progress_callback: Callable[[str], Awaitable[None]] | None = None,
) -> dict[str, Any]:

    async def _notify(msg: str) -> None:
        if progress_callback:
            await progress_callback(msg)

    await _notify("Evaluating base prompt…")
    best_prompt = base_prompt
    best_result = await run_dataset(adapter, best_prompt, testcases, judge_model)
    prev_best_objective = best_result["avg_objective"]
    await _notify(f"Base score: {prev_best_objective:.4f}")

    for i in range(iterations):
        candidates = list(basic_mutations(best_prompt, testcases=testcases))
        await _notify(f"Iteration {i + 1}/{iterations}: generated {len(candidates)} mutations.")

        if use_rewriter:
            rw_model = rewriter_model or judge_model
            await _notify("Generating LLM rewrite…")
            rewritten = await rewrite_prompt(
                adapter,
                rw_model,
                best_prompt,
                current_score=best_result.get("avg_judge_score"),
                judge_reasoning=None,
            )
            if rewritten is not None:
                candidates.append(rewritten)
                await _notify(f"Rewrite added — evaluating {len(candidates)} candidates in parallel…")
            else:
                await _notify(f"Evaluating {len(candidates)} candidates in parallel…")
        else:
            await _notify(f"Evaluating {len(candidates)} candidates in parallel…")

        cand_results = await asyncio.gather(
            *[run_dataset(adapter, cand, testcases, judge_model) for cand in candidates]
        )

        for cand, result in zip(candidates, cand_results):
            if result["avg_objective"] > best_result["avg_objective"]:
                best_result = result
                best_prompt = cand

        current_objective = best_result["avg_objective"]
        await _notify(
            f"Iteration {i + 1} done. Best: {current_objective:.4f} "
            f"(prompt: {best_prompt.name})"
        )

        if current_objective - prev_best_objective < min_delta:
            await _notify("Early stop: improvement below threshold.")
            break
        prev_best_objective = current_objective

    await _notify("Optimization complete.")
    return {
        "best_prompt": best_prompt,
        "best_result": best_result,
    }
