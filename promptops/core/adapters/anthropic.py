from __future__ import annotations

import os
import time
from typing import Any, Dict

from .base import BaseAdapter, ModelResponse


class AnthropicAdapter(BaseAdapter):
    def __init__(self, api_key: str | None = None, timeout_s: float = 120.0):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self.timeout_s = timeout_s

    async def generate(
        self,
        model: str,
        system: str,
        prompt: str,
        params: Dict[str, Any],
    ) -> ModelResponse:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=self.api_key, timeout=self.timeout_s)

        max_tokens = params.get("max_tokens", 1024)
        kwargs: Dict[str, Any] = {"max_tokens": max_tokens}
        if "temperature" in params:
            kwargs["temperature"] = params["temperature"]

        start = time.time()
        resp = await client.messages.create(
            model=model,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        )
        latency_ms = (time.time() - start) * 1000.0

        output = ""
        for block in resp.content:
            if hasattr(block, "text"):
                output += block.text

        usage = resp.usage
        prompt_tokens = usage.input_tokens if usage else None
        completion_tokens = usage.output_tokens if usage else None
        total_tokens = None
        if prompt_tokens is not None and completion_tokens is not None:
            total_tokens = prompt_tokens + completion_tokens

        return ModelResponse(
            output=output,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            raw={},
        )

    async def health_check(self) -> bool:
        try:
            import anthropic

            client = anthropic.AsyncAnthropic(api_key=self.api_key, timeout=5.0)
            await client.messages.create(
                model="claude-haiku-4-5-20251001",
                system="ping",
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
            )
            return True
        except Exception:
            return False
