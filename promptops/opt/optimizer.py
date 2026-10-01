from __future__ import annotations

import asyncio
import math
from typing import Any, Awaitable, Callable

from promptops.core.prompt import Prompt
from promptops.core.adapters.base import BaseAdapter
from promptops.core.runner import run_dataset
from promptops.tests.testcase import TestCase
from promptops.opt.mutations import basic_mutations, is_param_only_variant
from promptops.opt.rewriter import rewrite_prompt


async def _evaluate(
    adapter: BaseAdapter,
    prompt: Prompt,
    testcases: list[TestCase],
    judge_model: str,
    repeats: int,
    judge_adapter: BaseAdapter | None = None,
) -> dict[str, Any]:
    """Run the same prompt `repeats` times and average the results.

    A single run's objective conflates real prompt quality with generation sampling
    noise (whenever prompt.params["temperature"] > 0). Repeating the identical prompt
    against the identical test cases and judge isolates that noise so accept/reject
    decisions in the loop below aren't driven by a single lucky or unlucky sample.
    """
    run_results = await asyncio.gather(
        *[
            run_dataset(adapter, prompt, testcases, judge_model, judge_adapter=judge_adapter)
            for _ in range(repeats)
        ]
    )
    if repeats == 1:
        return run_results[0]

    avg_objective = sum(r["avg_objective"] for r in run_results) / repeats
    avg_judge_score = sum(r["avg_judge_score"] for r in run_results) / repeats
    avg_pass_rate = sum(r["pass_rate"] for r in run_results) / repeats

    avg_aggregate_metrics: dict[str, float | None] = {}
    for key in run_results[0]["aggregate_metrics"]:
        values = [
            r["aggregate_metrics"][key]
            for r in run_results
            if r["aggregate_metrics"].get(key) is not None
        ]
        avg_aggregate_metrics[key] = sum(values) / len(values) if values else None

    return {
        "run_id": run_results[-1]["run_id"],
        "run_ids": [r["run_id"] for r in run_results],
        "avg_judge_score": avg_judge_score,
        "avg_objective": avg_objective,
        "objective_runs": [r["avg_objective"] for r in run_results],
        "pass_rate": avg_pass_rate,
        "aggregate_metrics": avg_aggregate_metrics,
        "outputs": run_results[-1]["outputs"],
        "regression": any(r["regression"] for r in run_results),
        "regression_warning": next(
            (r["regression_warning"] for r in run_results if r["regression_warning"]), None
        ),
    }


def _significant_improvement(
    baseline: dict[str, Any], candidate: dict[str, Any], z: float = 1.5
) -> bool:
    """Approximate Welch's-t-test-style check: is candidate's mean objective higher than
    baseline's by more than the observed spread would explain by chance?

    This is a heuristic, not a real p-value — repeats is typically 3-5, so statistical
    power is low and `z` is a fixed threshold rather than a calibrated significance
    level. It exists to stop the loop from treating a within-noise difference as a real
    improvement; it will still occasionally accept noise or reject a real improvement.
    Falls back to a plain mean comparison when there isn't enough repeat data (fewer
    than 2 runs per side) to estimate variance.
    """
    base_runs = baseline.get("objective_runs")
    cand_runs = candidate.get("objective_runs")
    if not base_runs or not cand_runs or len(base_runs) < 2 or len(cand_runs) < 2:
        return candidate["avg_objective"] > baseline["avg_objective"]

    base_mean = sum(base_runs) / len(base_runs)
    cand_mean = sum(cand_runs) / len(cand_runs)
    base_var = sum((x - base_mean) ** 2 for x in base_runs) / (len(base_runs) - 1)
    cand_var = sum((x - cand_mean) ** 2 for x in cand_runs) / (len(cand_runs) - 1)
    pooled_stderr = math.sqrt(base_var / len(base_runs) + cand_var / len(cand_runs))
    if pooled_stderr == 0:
        return cand_mean > base_mean
    return (cand_mean - base_mean) > z * pooled_stderr


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
    repeats: int = 1,
    judge_adapter: BaseAdapter | None = None,
    significance_z: float = 1.5,
) -> dict[str, Any]:

    if repeats < 1:
        raise ValueError("repeats must be at least one")

    async def _notify(msg: str) -> None:
        if progress_callback:
            await progress_callback(msg)

    await _notify("Evaluating base prompt…")
    best_prompt = base_prompt
    best_result = await _evaluate(
        adapter, best_prompt, testcases, judge_model, repeats, judge_adapter=judge_adapter
    )
    baseline_result = best_result
    prev_best_objective = best_result["avg_objective"]
    await _notify(
        f"Base score: {prev_best_objective:.4f}; "
        f"pass rate: {best_result.get('pass_rate', 0.0) * 100:.0f}%"
        + (f" (avg of {repeats} runs)" if repeats > 1 else "")
    )

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
            *[
                _evaluate(adapter, cand, testcases, judge_model, repeats, judge_adapter=judge_adapter)
                for cand in candidates
            ]
        )

        for cand, result in zip(candidates, cand_results):
            if _significant_improvement(best_result, result, z=significance_z):
                best_result = result
                best_prompt = cand

        current_objective = best_result["avg_objective"]
        await _notify(
            f"Iteration {i + 1} done. Best: {current_objective:.4f} "
            f"pass rate: {best_result.get('pass_rate', 0.0) * 100:.0f}% "
            f"(prompt: {best_prompt.name})"
        )

        if current_objective - prev_best_objective < min_delta:
            await _notify("Early stop: improvement below threshold.")
            break
        prev_best_objective = current_objective

    await _notify("Optimization complete.")
    comparison = {
        "baseline_prompt_name": base_prompt.name,
        "best_prompt_name": best_prompt.name,
        "objective_delta": best_result.get("avg_objective", 0.0)
        - baseline_result.get("avg_objective", 0.0),
        "judge_score_delta": best_result.get("avg_judge_score", 0.0)
        - baseline_result.get("avg_judge_score", 0.0),
        "pass_rate_delta": best_result.get("pass_rate", 0.0)
        - baseline_result.get("pass_rate", 0.0),
        "improved": best_result.get("avg_objective", 0.0)
        > baseline_result.get("avg_objective", 0.0),
        "significant_improvement": _significant_improvement(
            baseline_result, best_result, z=significance_z
        ),
        "best_prompt_is_param_only_variant": is_param_only_variant(best_prompt),
    }
    return {
        "baseline_result": baseline_result,
        "best_prompt": best_prompt,
        "best_result": best_result,
        "comparison": comparison,
    }
