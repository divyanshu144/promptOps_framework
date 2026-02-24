from __future__ import annotations

import hashlib
import json
import time
from typing import Any

import mlflow

from promptops.core.prompt import Prompt
from promptops.core.adapter import OllamaAdapter
from promptops.eval.judge import judge_output
from promptops.eval.metrics import compute_metrics, RunMetrics
from promptops.tests.testcase import TestCase
from promptops.store.db import init_db, insert_run


def prompt_hash(prompt: Prompt) -> str:
    raw = json.dumps(prompt.model_dump(), sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def run_prompt(
    adapter: OllamaAdapter,
    prompt: Prompt,
    testcase: TestCase,
    judge_model: str,
) -> tuple[str, RunMetrics]:
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

    return resp.output, metrics


async def run_prompt_detailed(
    adapter: OllamaAdapter,
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
        "judge_reasoning": judge.reasoning,
        "metrics": metrics.model_dump(),
    }


async def run_dataset(
    adapter: OllamaAdapter,
    prompt: Prompt,
    testcases: list[TestCase],
    judge_model: str,
    mlflow_uri: str = "./mlruns",
) -> dict[str, Any]:
    init_db()
    mlflow.set_tracking_uri(mlflow_uri)

    outputs: list[str] = []
    metrics_list: list[RunMetrics] = []

    with mlflow.start_run() as run:
        mlflow.log_params(
            {
                "prompt_name": prompt.name,
                "model": prompt.model,
                "context_limit": prompt.context_limit,
                **prompt.params,
            }
        )

        for tc in testcases:
            output, metrics = await run_prompt(adapter, prompt, tc, judge_model)
            outputs.append(output)
            metrics_list.append(metrics)

        avg_score = sum(m.judge_score for m in metrics_list) / max(len(metrics_list), 1)
        avg_objective = sum(m.objective for m in metrics_list) / max(len(metrics_list), 1)

        mlflow.log_metric("avg_judge_score", avg_score)
        mlflow.log_metric("avg_objective", avg_objective)

        mlflow.log_text("\n---\n".join(outputs), "outputs.txt")

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
    }
    insert_run(run_data)

    return {
        "avg_judge_score": avg_score,
        "avg_objective": avg_objective,
        "outputs": outputs,
    }
