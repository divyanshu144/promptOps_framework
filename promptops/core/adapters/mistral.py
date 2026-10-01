from __future__ import annotations

from .openai import OpenAIAdapter


class MistralAdapter(OpenAIAdapter):
    """Mistral's OpenAI-compatible chat API through the existing async SDK."""

    provider = "mistral"
    api_key_env = "MISTRAL_API_KEY"

    def __init__(self, api_key: str | None = None, timeout_s: float = 120.0,
                 base_url: str = "https://api.mistral.ai/v1"):
        super().__init__(api_key=api_key, timeout_s=timeout_s, base_url=base_url)

    def _generation_options(self, params):
        options = super()._generation_options(params)
        options.pop("max_completion_tokens", None)
        if "max_tokens" not in options and "max_completion_tokens" in params:
            options["max_tokens"] = params["max_completion_tokens"]
        if "seed" in params:
            options["random_seed"] = params["seed"]
        return options
