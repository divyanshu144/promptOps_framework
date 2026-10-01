from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Dict


@dataclass
class TestCase:
    __test__ = False
    input: Dict[str, Any]
    expected: str | None = None
    rubric: Dict[str, Any] | None = None
    threshold: float = 0.7
    expected_tools: list[str] | None = None
    relevant_doc_ids: list[str] | None = None
    expected_claims: list[str] | None = None


    def __post_init__(self) -> None:
        if not math.isfinite(self.threshold) or not 0 <= self.threshold <= 1:
            raise ValueError("Case threshold must be finite and between zero and one")
        budgets = (self.rubric or {}).get("budgets", {})
        if not isinstance(budgets, dict):
            raise ValueError("Case budgets must be an object")
        for key, value in budgets.items():
            if key not in {"max_latency_ms", "max_cost_usd", "max_output_words"}:
                raise ValueError(f"Unknown case budget: {key}")
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                raise ValueError(f"Case budget {key} must be finite and non-negative")
