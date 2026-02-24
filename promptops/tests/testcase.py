from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class TestCase:
    input: Dict[str, Any]
    expected: str | None = None
    rubric: Dict[str, Any] | None = None
