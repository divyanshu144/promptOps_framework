from __future__ import annotations

from typing import Any


def classify_failures(*, passed: bool, criteria: dict[str, float], metrics: dict[str, Any],
                      output: str, budgets: dict[str, Any] | None = None, threshold: float = 0.7) -> list[str]:
    """Evidence-based likely causes. Budgets are explicit case limits, not inferred costs."""
    labels = []
    budgets = budgets or {}
    if not passed:
        for label, keys in {
            "hallucination": ("faithfulness", "groundedness", "factuality"),
            "missing_citation": ("citation_coverage",),
            "incomplete_answer": ("completeness",),
            "wrong_or_irrelevant_answer": ("answer_relevance", "correctness"),
            "unsafe_output": ("safety",),
        }.items():
            if any(criteria.get(k, 1.0) < threshold for k in keys):
                labels.append(label)
        if metrics.get("format_valid") is False:
            labels.append("format_violation")
    for label, key, limit in (
        ("latency_regression", "latency_ms", "max_latency_ms"),
        ("cost_regression", "cost_usd", "max_cost_usd"),
    ):
        if budgets.get(limit) is not None:
            if metrics.get(key) is None:
                labels.append(f"{key}_unavailable")
            elif metrics[key] > budgets[limit]:
                labels.append(label)
    if budgets.get("max_output_words") is not None and len(output.split()) > budgets["max_output_words"]:
        labels.append("verbosity")
    if not passed and not labels:
        labels.append("unclassified")
    return labels
