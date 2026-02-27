from __future__ import annotations

import asyncio
import hashlib
import json
import time
import warnings
from typing import Any

import mlflow

from promptops.core.prompt import Prompt
from promptops.core.adapters.base import BaseAdapter
from promptops.eval.judge import judge_output
from promptops.eval.metrics import compute_metrics, RunMetrics
from promptops.tests.testcase import TestCase
from promptops.store.db import (
    init_db,
    insert_run,
    insert_run_result,
    get_best_for_prompt,
)


def prompt_hash(prompt: Prompt) -> str:
    raw = json.dumps(prompt.model_dump(), sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def run_prompt(
    adapter: BaseAdapter,
    prompt: Prompt,
    testcase: TestCase,
    judge_model: str,
) -> tuple[str, RunMetrics, dict[str, Any]]:
    rendered = prompt.render(**testcase.input)

    start = time.time()
    resp = await adapter.generate(
        model=prompt.model,
        system=prompt.system,
        prompt=rendered,
        params=prompt.params,
    )
    latency_ms = (time.time() - start) * 1000.0

    judge = await judge_output(
        adapter=adapter,
        model=judge_model,
        rubric=testcase.rubric or {"quality": 1.0},
        user_input=testcase.input,
        assistant_output=resp.output,
        expected=testcase.expected,
    )

    format_valid = None
    if prompt.output_format == "json" or prompt.output_schema is not None:
        try:
            _ = json.loads(resp.output)
            format_valid = True
        except Exception:
            format_valid = False

    if format_valid is False:
        judge.score = min(judge.score, 0.2)

    metrics = compute_metrics(
        judge_score=judge.score,
        prompt_tokens=resp.prompt_tokens,
        completion_tokens=resp.completion_tokens,
        latency_ms=latency_ms,
        context_limit=prompt.context_limit,
        format_valid=format_valid,
    )

    judge_info = {
        "judge_score": judge.score,
        "judge_criteria": judge.criteria,
        "judge_reasoning": judge.reasoning,
    }
    return resp.output, metrics, judge_info


async def run_prompt_detailed(
    adapter: BaseAdapter,
    prompt: Prompt,
    testcase: TestCase,
    judge_model: str,
) -> dict[str, Any]:
    try:
        rendered = prompt.render(**testcase.input)
    except Exception as e:
        return {
            "input": testcase.input,
            "output": "",
            "judge_score": 0.0,
            "judge_criteria": {},
            "judge_reasoning": f"Render error: {e}",
            "metrics": {},
        }

    start = time.time()
    resp = await adapter.generate(
        model=prompt.model,
        system=prompt.system,
        prompt=rendered,
        params=prompt.params,
    )
    latency_ms = (time.time() - start) * 1000.0

    judge = await judge_output(
        adapter=adapter,
        model=judge_model,
        rubric=testcase.rubric or {"quality": 1.0},
        user_input=testcase.input,
        assistant_output=resp.output,
        expected=testcase.expected,
    )

    format_valid = None
    if prompt.output_format == "json" or prompt.output_schema is not None:
        try:
            _ = json.loads(resp.output)
            format_valid = True
        except Exception:
            format_valid = False

    if format_valid is False:
        judge.score = min(judge.score, 0.2)

    metrics = compute_metrics(
        judge_score=judge.score,
        prompt_tokens=resp.prompt_tokens,
        completion_tokens=resp.completion_tokens,
        latency_ms=latency_ms,
        context_limit=prompt.context_limit,
        format_valid=format_valid,
    )

    return {
        "input": testcase.input,
        "output": resp.output,
        "judge_score": judge.score,
        "judge_criteria": judge.criteria,
        "judge_reasoning": judge.reasoning,
        "metrics": metrics.model_dump(),
    }


async def run_dataset(
    adapter: BaseAdapter,
    prompt: Prompt,
    testcases: list[TestCase],
    judge_model: str,
    mlflow_uri: str = "./mlruns",
) -> dict[str, Any]:
    init_db()

    # Health check before running
    healthy = await adapter.health_check()
    if not healthy:
        raise RuntimeError("Model provider unreachable. Check that the service is running.")

    mlflow.set_tracking_uri(mlflow_uri)

    with mlflow.start_run() as run:
        mlflow.log_params(
            {
                "prompt_name": prompt.name,
                "model": prompt.model,
                "provider": prompt.provider,
                "context_limit": prompt.context_limit,
                **prompt.params,
            }
        )

        # Run all test cases in parallel
        tasks = [run_prompt(adapter, prompt, tc, judge_model) for tc in testcases]
        results = await asyncio.gather(*tasks)

        outputs: list[str] = []
        metrics_list: list[RunMetrics] = []
        judge_infos: list[dict[str, Any]] = []

        for output, metrics, judge_info in results:
            outputs.append(output)
            metrics_list.append(metrics)
            judge_infos.append(judge_info)

        avg_score = sum(m.judge_score for m in metrics_list) / max(len(metrics_list), 1)
        avg_objective = sum(m.objective for m in metrics_list) / max(len(metrics_list), 1)

        mlflow.log_metric("avg_judge_score", avg_score)
        mlflow.log_metric("avg_objective", avg_objective)
        mlflow.log_text("\n---\n".join(outputs), "outputs.txt")

    # Regression detection: compare against previous best for this prompt
    prev_best = get_best_for_prompt(prompt.name)
    regression = False
    regression_warning: str | None = None
    if prev_best is not None and prev_best.get("objective") is not None:
        if avg_objective < prev_best["objective"]:
            regression = True
            regression_warning = (
                f"Regression detected: objective {avg_objective:.4f} < "
                f"previous best {prev_best['objective']:.4f}"
            )
            warnings.warn(regression_warning, stacklevel=2)

    run_data = {
        "prompt_name": prompt.name,
        "prompt_hash": prompt_hash(prompt),
        "model": prompt.model,
        "run_id": run.info.run_id,
        "mlflow_uri": mlflow_uri,
        "judge_score": avg_score,
        "objective": avg_objective,
        "prompt_tokens": None,
        "completion_tokens": None,
        "total_tokens": None,
        "latency_ms": None,
        "context_window_used": None,
        "regression": regression,
    }
    db_run_id = insert_run(run_data)

    # Store per-test-case results
    for idx, (tc, output, metrics, judge_info) in enumerate(
        zip(testcases, outputs, metrics_list, judge_infos)
    ):
        insert_run_result(
            run_id=db_run_id,
            test_idx=idx,
            input_data=tc.input,
            expected=tc.expected,
            output=output,
            judge_score=judge_info["judge_score"],
            judge_criteria=judge_info["judge_criteria"],
            judge_reasoning=judge_info["judge_reasoning"],
            metrics=metrics.model_dump(),
        )

    return {
        "run_id": db_run_id,
        "avg_judge_score": avg_score,
        "avg_objective": avg_objective,
        "outputs": outputs,
        "regression": regression,
        "regression_warning": regression_warning,
    }
