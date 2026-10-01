from __future__ import annotations

import os
import time
from typing import Any, Dict

import httpx

from .base import BaseAdapter, ModelResponse
from .cost import cost_trace


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

        if not self.api_key:
            raise ValueError("Configure ANTHROPIC_API_KEY for Claude")
        client = anthropic.AsyncAnthropic(api_key=self.api_key, timeout=self.timeout_s)

        max_tokens = params.get("max_tokens", 1024)
        kwargs: Dict[str, Any] = {"max_tokens": max_tokens}
        if "temperature" in params:
            kwargs["temperature"] = params["temperature"]

        start = time.time()
        try:
            resp = await client.messages.create(
                model=model,
                system=system,
                messages=[{"role": "user", "content": prompt}],
                **kwargs,
            )
        finally:
            await client.close()
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
            raw=cost_trace("anthropic", model, prompt_tokens, completion_tokens),
        )

    async def health_check(self) -> bool:
        if not self.api_key:
            return False
        try:
            # Authenticate without generating a billable ping completion.
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    "https://api.anthropic.com/v1/models",
                    headers={"x-api-key": self.api_key, "anthropic-version": "2023-06-01"},
                )
                return response.status_code == 200
        except httpx.HTTPError:
            return False
