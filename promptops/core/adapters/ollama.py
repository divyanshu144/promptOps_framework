from __future__ import annotations

import os
from typing import Any, Dict

import httpx

from .base import BaseAdapter, ModelResponse
from .cost import cost_trace


class OllamaAdapter(BaseAdapter):
    def __init__(self, base_url: str | None = None, timeout_s: float = 120.0):
        self.base_url = base_url or os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.timeout_s = timeout_s

    async def generate(
        self,
        model: str,
        system: str,
        prompt: str,
        params: Dict[str, Any],
    ) -> ModelResponse:
        # Map max_tokens -> num_predict for Ollama
        mapped_params = {k: v for k, v in params.items() if k not in {"max_tokens", "format", "keep_alive"}}
        if "max_tokens" in params:
            mapped_params["num_predict"] = params["max_tokens"]

        url = f"{self.base_url}/api/generate"
        payload = {
            "model": model,
            "system": system,
            "prompt": prompt,
            "stream": False,
            "options": mapped_params,
            **{k: params[k] for k in ("format", "keep_alive") if k in params},
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
            latency_ms=data["total_duration"] / 1_000_000.0 if data.get("total_duration") is not None else None,
            raw={**data, **cost_trace("ollama", model, prompt_tokens, completion_tokens)},
        )

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False
