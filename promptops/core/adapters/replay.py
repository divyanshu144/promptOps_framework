from __future__ import annotations

from promptops.core.adapters.base import BaseAdapter, ModelResponse


class ReplayAdapter(BaseAdapter):
    """Explicit offline fixture replay, keyed by fully rendered generation prompt."""

    def __init__(self, responses: dict):
        self.responses = responses

    async def health_check(self) -> bool:
        return True

    async def generate(self, model, system, prompt, params) -> ModelResponse:
        if prompt not in self.responses:
            raise ValueError("No recorded fixture for rendered prompt")
        return ModelResponse.model_validate(self.responses[prompt])
