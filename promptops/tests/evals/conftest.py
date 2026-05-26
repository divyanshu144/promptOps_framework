from __future__ import annotations

import asyncio
import os
import pytest

from promptops.core.adapters.ollama import OllamaAdapter
from promptops.core.prompt import Prompt
from promptops.eval.deepeval_harness import PromptOpsDeepEvalLLM


async def _is_healthy(adapter: OllamaAdapter) -> bool:
    return await adapter.health_check()


@pytest.fixture(scope="session")
def adapter():
    url = os.getenv("OLLAMA_URL", "http://localhost:11434")
    a = OllamaAdapter(url)
    if not asyncio.run(_is_healthy(a)):
        pytest.skip("Ollama unreachable — start Ollama or set OLLAMA_URL to run eval tests")
    return a


@pytest.fixture(scope="session")
def default_prompt():
    return Prompt(
        name="eval_test_prompt",
        system="You are a helpful assistant.",
        template="{input}",
        model="llama3.1",
        params={"temperature": 0.2, "max_tokens": 200},
        context_limit=4096,
        provider="ollama",
    )


@pytest.fixture(scope="session")
def deepeval_llm(adapter, default_prompt):
    return PromptOpsDeepEvalLLM(adapter=adapter, model=default_prompt.model)


def generate_output(adapter, prompt: Prompt, text: str) -> str:
    """Synchronous helper: renders prompt, calls adapter, returns raw output string."""
    async def _run() -> str:
        rendered = prompt.render(input=text)
        resp = await adapter.generate(
            model=prompt.model,
            system=prompt.system,
            prompt=rendered,
            params=prompt.params,
        )
        return resp.output
    return asyncio.run(_run())
