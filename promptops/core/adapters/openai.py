from __future__ import annotations

import os
import time
from typing import Any, Dict

from .base import BaseAdapter, ModelResponse


class OpenAIAdapter(BaseAdapter):
    def __init__(self, api_key: str | None = None, timeout_s: float = 120.0):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.timeout_s = timeout_s

    async def generate(
        self,
        model: str,
        system: str,
        prompt: str,
        params: Dict[str, Any],
    ) -> ModelResponse:
        import openai

        client = openai.AsyncOpenAI(api_key=self.api_key, timeout=self.timeout_s)

        kwargs: Dict[str, Any] = {}
        if "max_tokens" in params:
            kwargs["max_tokens"] = params["max_tokens"]
        if "temperature" in params:
            kwargs["temperature"] = params["temperature"]

        start = time.time()
        resp = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            **kwargs,
        )
        latency_ms = (time.time() - start) * 1000.0

        choice = resp.choices[0]
        usage = resp.usage

        return ModelResponse(
            output=choice.message.content or "",
            prompt_tokens=usage.prompt_tokens if usage else None,
            completion_tokens=usage.completion_tokens if usage else None,
            total_tokens=usage.total_tokens if usage else None,
            latency_ms=latency_ms,
            raw={},
        )

    async def health_check(self) -> bool:
        try:
            import openai

            client = openai.AsyncOpenAI(api_key=self.api_key, timeout=5.0)
            await client.models.list()
            return True
        except Exception:
            return False
