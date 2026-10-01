from __future__ import annotations

import os
import time
from typing import Any, Dict

from .base import BaseAdapter, ModelResponse
from .cost import cost_trace


class OpenAIAdapter(BaseAdapter):
    provider = "openai"
    api_key_env = "OPENAI_API_KEY"

    def __init__(self, api_key: str | None = None, timeout_s: float = 120.0,
                 base_url: str | None = None):
        self.api_key = api_key or os.getenv(self.api_key_env, "")
        self.timeout_s = timeout_s
        self.base_url = base_url

    def _client_options(self, timeout: float) -> dict[str, Any]:
        options = {"api_key": self.api_key, "timeout": timeout}
        if self.base_url is not None:
            options["base_url"] = self.base_url
        return options

    def _generation_options(self, params: Dict[str, Any]) -> Dict[str, Any]:
        options = {key: params[key] for key in
                   ("max_tokens", "max_completion_tokens", "temperature", "top_p", "stop")
                   if key in params}
        if params.get("format") == "json":
            options["response_format"] = {"type": "json_object"}
        return options

    async def generate(
        self,
        model: str,
        system: str,
        prompt: str,
        params: Dict[str, Any],
    ) -> ModelResponse:
        import openai

        if not self.api_key:
            raise ValueError(f"Configure {self.api_key_env} for {self.provider}")
        client = openai.AsyncOpenAI(**self._client_options(self.timeout_s))
        kwargs = self._generation_options(params)

        start = time.time()
        try:
            resp = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                **kwargs,
            )
        finally:
            await client.close()
        latency_ms = (time.time() - start) * 1000.0

        choice = resp.choices[0]
        usage = resp.usage

        return ModelResponse(
            output=choice.message.content or "",
            prompt_tokens=usage.prompt_tokens if usage else None,
            completion_tokens=usage.completion_tokens if usage else None,
            total_tokens=usage.total_tokens if usage else None,
            latency_ms=latency_ms,
            raw=cost_trace(self.provider, model, usage.prompt_tokens if usage else None,
                           usage.completion_tokens if usage else None),
        )

    async def health_check(self) -> bool:
        try:
            import openai

            if not self.api_key:
                return False
            client = openai.AsyncOpenAI(**self._client_options(5.0))
            try:
                await client.models.list()
                return True
            finally:
                await client.close()
        except Exception:
            return False
