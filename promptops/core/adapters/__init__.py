from __future__ import annotations

from .base import BaseAdapter, ModelResponse
from .ollama import OllamaAdapter
from .openai import OpenAIAdapter
from .anthropic import AnthropicAdapter


def make_adapter(provider: str, **kwargs) -> BaseAdapter:
    match provider:
        case "ollama":
            return OllamaAdapter(**kwargs)
        case "openai":
            return OpenAIAdapter(**kwargs)
        case "anthropic":
            return AnthropicAdapter(**kwargs)
        case _:
            raise ValueError(f"Unknown provider: {provider!r}. Choose from: ollama, openai, anthropic")


__all__ = [
    "BaseAdapter",
    "ModelResponse",
    "OllamaAdapter",
    "OpenAIAdapter",
    "AnthropicAdapter",
    "make_adapter",
]
