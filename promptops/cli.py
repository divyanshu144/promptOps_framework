from __future__ import annotations

import asyncio
import typer

from promptops.core.adapter import OllamaAdapter
from promptops.core.prompt import Prompt
from promptops.core.runner import run_dataset
from promptops.opt.optimizer import optimize_prompt
from promptops.tests.dataset import demo_dataset

app = typer.Typer(add_completion=False)


@app.command()
def run(
    model: str = "llama3.1",
    judge_model: str = "llama3.1",
):
    prompt = Prompt(
        name="demo_prompt",
        system="You are a helpful assistant.",
        template="{input}",
        model=model,
        params={"temperature": 0.2, "max_tokens": 200},
    )

    async def _run():
        adapter = OllamaAdapter()
        results = await run_dataset(adapter, prompt, demo_dataset(), judge_model)
        return results

    results = asyncio.run(_run())
    typer.echo(results)


@app.command()
def optimize(
    model: str = "llama3.1",
    judge_model: str = "llama3.1",
    iterations: int = 2,
    use_rewriter: bool = True,
    rewriter_model: str | None = None,
):
    prompt = Prompt(
        name="demo_prompt",
        system="You are a helpful assistant.",
        template="{input}",
        model=model,
        params={"temperature": 0.2, "max_tokens": 200},
    )

    async def _run():
        adapter = OllamaAdapter()
        results = await optimize_prompt(
            adapter,
            prompt,
            demo_dataset(),
            judge_model,
            iterations,
            use_rewriter,
            rewriter_model,
        )
        return results

    results = asyncio.run(_run())
    typer.echo(results)
