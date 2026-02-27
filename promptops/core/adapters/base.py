from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

from pydantic import BaseModel


class ModelResponse(BaseModel):
    output: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    latency_ms: float | None = None
    raw: Dict[str, Any] = {}


class BaseAdapter(ABC):
    @abstractmethod
    async def generate(
        self,
        model: str,
        system: str,
        prompt: str,
        params: Dict[str, Any],
    ) -> ModelResponse: ...

    @abstractmethod
    async def health_check(self) -> bool: ...
