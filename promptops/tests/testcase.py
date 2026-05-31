from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class TestCase:
    __test__ = False
    input: Dict[str, Any]
    expected: str | None = None
    rubric: Dict[str, Any] | None = None
    threshold: float = 0.7
