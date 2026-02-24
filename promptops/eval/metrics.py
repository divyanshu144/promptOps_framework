from __future__ import annotations

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
    objective: float


def compute_metrics(
    judge_score: float,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    latency_ms: float | None,
    context_limit: int,
    format_valid: bool | None = None,
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
        objective=objective,
    )
