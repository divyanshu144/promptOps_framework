from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
import warnings
from typing import Any

import mlflow

from promptops.core.prompt import Prompt
from promptops.core.adapters.base import BaseAdapter
from promptops.eval.judge import judge_output
from promptops.eval.metrics import (
    aggregate_eval_metrics,
    compute_metrics,
    score_groundedness,
    score_retrieval_precision,
    score_tool_call_accuracy,
    RunMetrics,
)
from promptops.tests.testcase import TestCase
from promptops.store.db import (
    init_db,
    insert_run,
    insert_run_result,
    get_best_for_prompt,
)
from promptops.eval.failures import classify_failures
from promptops.eval.harness import EvalHarness
from promptops.eval.llm_judge_harness import LLMJudgeHarness


def prompt_hash(prompt: Prompt) -> str:
    raw = json.dumps(prompt.model_dump(), sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def run_prompt(
    adapter: BaseAdapter,
    prompt: Prompt,
    testcase: TestCase,
    judge_model: str,
    harness: EvalHarness | None = None,
    judge_adapter: BaseAdapter | None = None,
) -> tuple[str, RunMetrics, dict[str, Any]]:
    if harness is None:
        harness = LLMJudgeHarness(judge_adapter or adapter, judge_model)

    rendered = prompt.render(**testcase.input)

    start = time.time()
    resp = await adapter.generate(
        model=prompt.model,
        system=prompt.system,
        prompt=rendered,
        params=prompt.params,
    )
    latency_ms = resp.latency_ms if resp.latency_ms is not None else (time.time() - start) * 1000.0

    judge = await harness.evaluate(
        user_input=testcase.input,
        actual_output=resp.output,
        expected_output=testcase.expected,
        rubric=testcase.rubric,
    )

    format_valid = None
    if prompt.output_format == "json" or prompt.output_schema is not None:
        try:
            parsed = json.loads(resp.output)
            if prompt.output_schema is not None:
                from jsonschema import validate
                validate(parsed, prompt.output_schema)
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

    passed = judge.score >= testcase.threshold and format_valid is not False
    raw_trace = resp.raw or {}
    tool_call_accuracy = score_tool_call_accuracy(
        testcase.expected_tools,
        raw_trace.get("tool_calls"),
    )
    retrieval_precision = score_retrieval_precision(
        testcase.relevant_doc_ids,
        raw_trace.get("retrieved_docs"),
    )
    groundedness_score = score_groundedness(
        judge_score=judge.score,
        judge_criteria=judge.criteria,
        expected_claims=testcase.expected_claims,
        output=resp.output,
    )
    if not any(k in judge.criteria for k in ("groundedness", "factuality", "faithfulness")):
        groundedness_score = None
    cost_usd = raw_trace.get("cost_usd")
    metrics = metrics.model_copy(
        update={
            **{key: judge.criteria.get(key) for key in (
                "context_relevance", "citation_coverage", "answer_relevance", "unsupported_claim_rate"
            )},
            "cost_usd": cost_usd if isinstance(cost_usd, int | float) else None,
            "task_success": passed,
            "tool_call_accuracy": tool_call_accuracy,
            "retrieval_precision": retrieval_precision,
            "groundedness_score": groundedness_score,
            "hallucination_rate": 1.0 - groundedness_score if groundedness_score is not None else None,
        }
    )
    failure_labels = classify_failures(
        passed=passed, criteria=judge.criteria, metrics=metrics.model_dump(),
        output=resp.output, budgets=(testcase.rubric or {}).get("budgets"), threshold=testcase.threshold,
    )
    if failure_labels:
        passed = False
        metrics = metrics.model_copy(update={"task_success": False})
    judge_info = {
        "failure_labels": failure_labels,
        "judge_score": judge.score,
        "judge_criteria": judge.criteria,
        "judge_reasoning": judge.reasoning,
        "passed": passed,
        "trace": {
            "tool_calls": raw_trace.get("tool_calls", []),
            "retrieved_docs": raw_trace.get("retrieved_docs", []),
            "citations": raw_trace.get("citations", []),
            "cost_usd": metrics.cost_usd,
            "cost_source": raw_trace.get("cost_source"),
        },
    }
    return resp.output, metrics, judge_info


async def run_prompt_detailed(
    adapter: BaseAdapter,
    prompt: Prompt,
    testcase: TestCase,
    judge_model: str,
    judge_adapter: BaseAdapter | None = None,
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
    latency_ms = resp.latency_ms if resp.latency_ms is not None else (time.time() - start) * 1000.0

    judge = await judge_output(
        adapter=judge_adapter or adapter,
        model=judge_model,
        rubric=testcase.rubric or {"quality": 1.0},
        user_input=testcase.input,
        assistant_output=resp.output,
        expected=testcase.expected,
    )

    format_valid = None
    if prompt.output_format == "json" or prompt.output_schema is not None:
        try:
            parsed = json.loads(resp.output)
            if prompt.output_schema is not None:
                from jsonschema import validate
                validate(parsed, prompt.output_schema)
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
    mlflow_uri: str | None = None,
    harness: EvalHarness | None = None,
    suite_id: int | None = None,
    eval_harness_name: str | None = None,
    release_label: str | None = None,
    judge_adapter: BaseAdapter | None = None,
) -> dict[str, Any]:
    if harness is None:
        if judge_adapter is None and judge_model == prompt.model:
            warnings.warn(
                f"Judge model '{judge_model}' is the same as the prompt's generation "
                f"model '{prompt.model}', evaluated through the same adapter — the "
                "model may be evaluating its own output, which can bias scores toward "
                "self-preference. Pass a different judge_model or a separate "
                "judge_adapter to avoid this.",
                stacklevel=2,
            )
        harness = LLMJudgeHarness(judge_adapter or adapter, judge_model)

    if not testcases:
        raise ValueError("Cannot evaluate an empty suite")
    init_db()

    # Health check before running
    healthy = await adapter.health_check()
    if not healthy:
        raise RuntimeError("Model provider unreachable. Check that the service is running.")

    tasks = [
        run_prompt(adapter, prompt, tc, judge_model, harness=harness, judge_adapter=judge_adapter)
        for tc in testcases
    ]
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
    pass_rate = sum(1 for ji in judge_infos if ji["passed"]) / max(len(judge_infos), 1)
    aggregate_metrics = aggregate_eval_metrics(metrics_list)

    mlflow_uri = mlflow_uri or os.getenv("MLFLOW_TRACKING_URI", "./mlruns")
    mlflow.set_tracking_uri(mlflow_uri)

    if mlflow.active_run():
        mlflow.end_run()

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

        mlflow.log_metric("avg_judge_score", avg_score)
        mlflow.log_metric("avg_objective", avg_objective)
        mlflow.log_metric("pass_rate", pass_rate)
        for key, value in aggregate_metrics.model_dump().items():
            if value is not None:
                mlflow.log_metric(key, value)
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
        "pass_rate": pass_rate,
        "prompt_tokens": None,
        "completion_tokens": None,
        "total_tokens": None,
        "latency_ms": None,
        "context_window_used": None,
        "regression": regression,
        "suite_id": suite_id,
        "eval_harness": eval_harness_name,
        "release_label": release_label,
        "aggregate_metrics": aggregate_metrics.model_dump(),
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
            metrics={**metrics.model_dump(), "trace": judge_info.get("trace", {}),
                     "failure_labels": judge_info["failure_labels"]},
            passed=judge_info["passed"],
        )

    return {
        "run_id": db_run_id,
        "avg_judge_score": avg_score,
        "avg_objective": avg_objective,
        "pass_rate": pass_rate,
        "aggregate_metrics": aggregate_metrics.model_dump(),
        "outputs": outputs,
        "regression": regression,
        "regression_warning": regression_warning,
    }
