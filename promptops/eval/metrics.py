from __future__ import annotations

import math
from statistics import median
from typing import Any

from pydantic import BaseModel


class RunMetrics(BaseModel):
    judge_score: float
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    latency_ms: float | None
    context_window_used: float | None
    token_penalty: float
    format_valid: bool | None = None
    format_penalty: float = 0.0
    cost_usd: float | None = None
    task_success: bool | None = None
    tool_call_accuracy: float | None = None
    retrieval_precision: float | None = None
    groundedness_score: float | None = None
    context_relevance: float | None = None
    citation_coverage: float | None = None
    answer_relevance: float | None = None
    unsupported_claim_rate: float | None = None
    hallucination_rate: float | None = None
    objective: float


class AggregateEvalMetrics(BaseModel):
    task_success_rate: float | None = None
    tool_call_accuracy: float | None = None
    retrieval_precision: float | None = None
    groundedness_score: float | None = None
    context_relevance: float | None = None
    citation_coverage: float | None = None
    answer_relevance: float | None = None
    unsupported_claim_rate: float | None = None
    hallucination_rate: float | None = None
    cost_per_successful_task: float | None = None
    cost_per_attempted_task: float | None = None
    latency_p50_ms: float | None = None
    latency_p95_ms: float | None = None


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * percentile
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (rank - low)


def _normalize_tool_name(tool_call: Any) -> str:
    if isinstance(tool_call, str):
        return tool_call
    if isinstance(tool_call, dict):
        for key in ("name", "tool", "tool_name", "function"):
            value = tool_call.get(key)
            if isinstance(value, str):
                return value
    return str(tool_call)


def score_tool_call_accuracy(
    expected_tools: list[str] | None,
    actual_tool_calls: list[Any] | None,
) -> float | None:
    if not expected_tools:
        return None
    actual = [_normalize_tool_name(call) for call in actual_tool_calls or []]
    if not actual:
        return 0.0
    matched = sum(1 for expected, actual_name in zip(expected_tools, actual) if expected == actual_name)
    missing = max(len(expected_tools) - len(actual), 0)
    extra = max(len(actual) - len(expected_tools), 0)
    denominator = len(expected_tools) + extra
    return max(0.0, (matched - missing) / max(denominator, 1))


def score_retrieval_precision(
    relevant_doc_ids: list[str] | None,
    retrieved_docs: list[Any] | None,
) -> float | None:
    if not relevant_doc_ids:
        return None
    retrieved_ids: list[str] = []
    for doc in retrieved_docs or []:
        if isinstance(doc, str):
            retrieved_ids.append(doc)
        elif isinstance(doc, dict):
            doc_id = doc.get("id") or doc.get("doc_id") or doc.get("source_id")
            if doc_id is not None:
                retrieved_ids.append(str(doc_id))
    if not retrieved_ids:
        return 0.0
    relevant = set(relevant_doc_ids)
    hits = sum(1 for doc_id in retrieved_ids if doc_id in relevant)
    return hits / len(retrieved_ids)


def score_groundedness(
    judge_score: float,
    judge_criteria: dict[str, float] | None,
    expected_claims: list[str] | None,
    output: str,
) -> float:
    criteria = judge_criteria or {}
    for key in ("groundedness", "factuality", "faithfulness"):
        value = criteria.get(key)
        if isinstance(value, int | float):
            return max(0.0, min(1.0, float(value)))

    if expected_claims:
        output_lower = output.lower()
        supported = sum(1 for claim in expected_claims if claim.lower() in output_lower)
        return supported / len(expected_claims)

    return max(0.0, min(1.0, judge_score))


def compute_metrics(
    judge_score: float,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    latency_ms: float | None,
    context_limit: int,
    format_valid: bool | None = None,
    cost_usd: float | None = None,
    task_success: bool | None = None,
    tool_call_accuracy: float | None = None,
    retrieval_precision: float | None = None,
    groundedness_score: float | None = None,
) -> RunMetrics:
    total_tokens = None
    if prompt_tokens is not None and completion_tokens is not None:
        total_tokens = prompt_tokens + completion_tokens

    context_window_used = None
    if total_tokens is not None and context_limit > 0:
        context_window_used = total_tokens / context_limit

    token_penalty = 0.0
    if total_tokens is not None:
        token_penalty = total_tokens / max(context_limit, 1)

    format_penalty = 0.0
    if format_valid is False:
        format_penalty = 0.2

    objective = judge_score - 0.2 * token_penalty - format_penalty
    if context_window_used is not None:
        objective -= 0.1 * context_window_used
    if latency_ms is not None:
        objective -= 0.0001 * latency_ms

    return RunMetrics(
        judge_score=judge_score,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        latency_ms=latency_ms,
        context_window_used=context_window_used,
        token_penalty=token_penalty,
        format_valid=format_valid,
        format_penalty=format_penalty,
        cost_usd=cost_usd,
        task_success=task_success,
        tool_call_accuracy=tool_call_accuracy,
        retrieval_precision=retrieval_precision,
        groundedness_score=groundedness_score,
        hallucination_rate=None if groundedness_score is None else 1.0 - groundedness_score,
        objective=objective,
    )


def aggregate_eval_metrics(metrics: list[RunMetrics]) -> AggregateEvalMetrics:
    successes = [m.task_success for m in metrics if m.task_success is not None]
    success_count = sum(1 for value in successes if value)
    total_cost = (sum(m.cost_usd for m in metrics)
                  if metrics and all(m.cost_usd is not None for m in metrics) else None)
    latencies = [m.latency_ms for m in metrics if m.latency_ms is not None]

    return AggregateEvalMetrics(
        task_success_rate=success_count / len(successes) if successes else None,
        tool_call_accuracy=_mean(
            [m.tool_call_accuracy for m in metrics if m.tool_call_accuracy is not None]
        ),
        retrieval_precision=_mean(
            [m.retrieval_precision for m in metrics if m.retrieval_precision is not None]
        ),
        groundedness_score=_mean(
            [m.groundedness_score for m in metrics if m.groundedness_score is not None]
        ),
        context_relevance=_mean([m.context_relevance for m in metrics if m.context_relevance is not None]),
        citation_coverage=_mean([m.citation_coverage for m in metrics if m.citation_coverage is not None]),
        answer_relevance=_mean([m.answer_relevance for m in metrics if m.answer_relevance is not None]),
        unsupported_claim_rate=_mean([m.unsupported_claim_rate for m in metrics if m.unsupported_claim_rate is not None]),
        hallucination_rate=_mean(
            [m.hallucination_rate for m in metrics if m.hallucination_rate is not None]
        ),
        cost_per_successful_task=total_cost / success_count if success_count and total_cost is not None else None,
        cost_per_attempted_task=total_cost / len(metrics) if metrics and total_cost is not None else None,
        latency_p50_ms=median(latencies) if latencies else None,
        latency_p95_ms=_percentile(latencies, 0.95),
    )
