from __future__ import annotations

from typing import Any, Dict
from pydantic import BaseModel, Field
import string


class Prompt(BaseModel):
    name: str
    system: str
    template: str
    model: str
    params: Dict[str, Any] = Field(default_factory=dict)
    context_limit: int = 4096
    output_format: str | None = None
    output_schema: Dict[str, Any] | None = None
    provider: str = "ollama"

    def render(self, **kwargs: Any) -> str:
        class _SafeFormatter(string.Formatter):
            def get_value(self, key, args, kwargs):
                if isinstance(key, str) and key in kwargs:
                    return kwargs[key]
                return "{" + str(key) + "}"

        return _SafeFormatter().format(self.template, **kwargs)
