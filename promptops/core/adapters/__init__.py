from __future__ import annotations

from .base import BaseAdapter, ModelResponse
from .ollama import OllamaAdapter
from .openai import OpenAIAdapter
from .anthropic import AnthropicAdapter
from .mistral import MistralAdapter

DEFAULT_MODELS = {
    "ollama": "llama3.1",
    "openai": "gpt-4o-mini",
    "anthropic": "claude-haiku-4-5-20251001",
    "mistral": "mistral-small-latest",
}


def default_model(provider: str) -> str:
    canonical = "anthropic" if provider.strip().lower() == "claude" else provider.strip().lower()
    if canonical not in DEFAULT_MODELS:
        raise ValueError(f"Unknown provider: {provider!r}")
    return DEFAULT_MODELS[canonical]


def make_adapter(provider: str, **kwargs) -> BaseAdapter:
    match provider.strip().lower():
        case "ollama":
            return OllamaAdapter(**kwargs)
        case "openai":
            return OpenAIAdapter(**kwargs)
        case "anthropic" | "claude":
            return AnthropicAdapter(**kwargs)
        case "mistral":
            return MistralAdapter(**kwargs)
        case _:
            raise ValueError(f"Unknown provider: {provider!r}. Choose from: ollama, openai, anthropic (claude), mistral")


__all__ = [
    "BaseAdapter",
    "ModelResponse",
    "OllamaAdapter",
    "OpenAIAdapter",
    "AnthropicAdapter",
    "MistralAdapter",
    "default_model",
    "make_adapter",
]
