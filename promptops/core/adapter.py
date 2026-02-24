from __future__ import annotations

import os
from typing import Any, Dict
import httpx
from pydantic import BaseModel


class ModelResponse(BaseModel):
    output: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    latency_ms: float | None = None
    raw: Dict[str, Any] = {}


class OllamaAdapter:
    def __init__(self, base_url: str | None = None, timeout_s: float = 120.0):
        self.base_url = base_url or os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.timeout_s = timeout_s

    async def generate(self, model: str, system: str, prompt: str, params: Dict[str, Any]) -> ModelResponse:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": model,
            "system": system,
            "prompt": prompt,
            "stream": False,
            **params,
        }
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        prompt_tokens = data.get("prompt_eval_count")
        completion_tokens = data.get("eval_count")
        total_tokens = None
        if prompt_tokens is not None and completion_tokens is not None:
            total_tokens = prompt_tokens + completion_tokens

        return ModelResponse(
            output=data.get("response", ""),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=data.get("total_duration", 0) / 1_000_000.0,
            raw=data,
        )
