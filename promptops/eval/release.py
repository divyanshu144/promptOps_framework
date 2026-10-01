from __future__ import annotations

from typing import Any
import math

from pydantic import BaseModel, Field, field_validator


class ReleaseGateThresholds(BaseModel):
    minimums: dict[str, float] = Field(default_factory=dict)
    maximums: dict[str, float] = Field(default_factory=dict)
    max_regression: dict[str, float] = Field(default_factory=dict)


    @field_validator("minimums", "maximums", "max_regression")
    @classmethod
    def finite_thresholds(cls, values, info):
        if any(not math.isfinite(v) or (info.field_name == "max_regression" and v < 0) for v in values.values()):
            raise ValueError("Thresholds must be finite; regression allowances must be non-negative")
        return values


class ReleaseGateResult(BaseModel):
    passed: bool
    failures: list[str] = Field(default_factory=list)
    metrics: dict[str, float | None] = Field(default_factory=dict)
    baseline_metrics: dict[str, float | None] | None = None


DEFAULT_RELEASE_THRESHOLDS = ReleaseGateThresholds(
    minimums={
        "task_success_rate": 0.9,
        "tool_call_accuracy": 0.95,
        "retrieval_precision": 0.8,
        "groundedness_score": 0.9,
    },
    maximums={
        "hallucination_rate": 0.05,
        "latency_p95_ms": 8000.0,
    },
    max_regression={
        "task_success_rate": 0.02,
        "tool_call_accuracy": 0.02,
        "retrieval_precision": 0.05,
        "groundedness_score": 0.03,
    },
)


def _coerce_metrics(metrics: Any) -> dict[str, float | None]:
    if hasattr(metrics, "model_dump"):
        data = metrics.model_dump()
    else:
        data = dict(metrics or {})
    return {key: value for key, value in data.items() if isinstance(value, int | float) or value is None}


def evaluate_release_gate(
    metrics: Any,
    thresholds: ReleaseGateThresholds | None = None,
    baseline_metrics: Any | None = None,
) -> ReleaseGateResult:
    current = _coerce_metrics(metrics)
    # Require universal metrics by default. Explicit profiles remain fail-closed.
    if thresholds is None:
        thresholds = ReleaseGateThresholds(
            minimums={"task_success_rate": 0.9},
            maximums={"latency_p95_ms": 8000.0},
            max_regression={"task_success_rate": 0.02},
        )
    baseline = _coerce_metrics(baseline_metrics) if baseline_metrics is not None else None
    failures: list[str] = []

    for key, minimum in thresholds.minimums.items():
        value = current.get(key)
        if value is None or not math.isfinite(value):
            failures.append(f"{key} missing; required >= {minimum:g}")
        elif value < minimum:
            failures.append(f"{key} {value:.4g} < minimum {minimum:g}")

    for key, maximum in thresholds.maximums.items():
        value = current.get(key)
        if value is None or not math.isfinite(value):
            failures.append(f"{key} missing; required <= {maximum:g}")
        elif value > maximum:
            failures.append(f"{key} {value:.4g} > maximum {maximum:g}")

    if baseline is not None:
        for key, allowed_drop in thresholds.max_regression.items():
            value = current.get(key)
            base_value = baseline.get(key)
            if value is None or base_value is None or not math.isfinite(value) or not math.isfinite(base_value):
                failures.append(f"{key} missing in current or baseline; cannot check regression")
                continue
            drop = base_value - value
            if drop > allowed_drop:
                failures.append(
                    f"{key} regressed by {drop:.4g}; allowed drop {allowed_drop:g}"
                )

    return ReleaseGateResult(
        passed=not failures,
        failures=failures,
        metrics=current,
        baseline_metrics=baseline,
    )
