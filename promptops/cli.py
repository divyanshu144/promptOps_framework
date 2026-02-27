from __future__ import annotations

import asyncio
import sys

import typer

from promptops.core.adapters import make_adapter
from promptops.core.prompt import Prompt
from promptops.core.runner import run_dataset
from promptops.opt.optimizer import optimize_prompt
from promptops.tests.dataset import demo_dataset
from promptops.store.db import (
    init_db,
    list_suites,
    create_suite,
    delete_suite,
    get_suite,
)

app = typer.Typer(add_completion=False)
suites_app = typer.Typer()
app.add_typer(suites_app, name="suites")


@app.command()
def run(
    model: str = "llama3.1",
    judge_model: str = "llama3.1",
    provider: str = "ollama",
):
    prompt = Prompt(
        name="demo_prompt",
        system="You are a helpful assistant.",
        template="{input}",
        model=model,
        params={"temperature": 0.2, "max_tokens": 200},
        provider=provider,
    )

    async def _run():
        adapter = make_adapter(provider)
        results = await run_dataset(adapter, prompt, demo_dataset(), judge_model)
        return results

    results = asyncio.run(_run())

    if results.get("regression"):
        typer.echo(
            typer.style(
                f"\n⚠  REGRESSION: {results['regression_warning']}",
                fg=typer.colors.RED,
                bold=True,
            ),
            err=True,
        )

    typer.echo(results)


@app.command()
def optimize(
    model: str = "llama3.1",
    judge_model: str = "llama3.1",
    iterations: int = 2,
    use_rewriter: bool = True,
    rewriter_model: str | None = None,
    provider: str = "ollama",
):
    prompt = Prompt(
        name="demo_prompt",
        system="You are a helpful assistant.",
        template="{input}",
        model=model,
        params={"temperature": 0.2, "max_tokens": 200},
        provider=provider,
    )

    async def _run():
        adapter = make_adapter(provider)
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


# --- suites subcommands ---

@suites_app.command("list")
def suites_list():
    init_db()
    rows = list_suites()
    if not rows:
        typer.echo("No suites found.")
        return
    for s in rows:
        typer.echo(f"  [{s['id']}] {s['name']} — {s.get('case_count', 0)} cases — {s.get('description', '')}")


@suites_app.command("create")
def suites_create(
    name: str = typer.Argument(...),
    description: str = typer.Option("", "--description", "-d"),
):
    init_db()
    suite_id = create_suite(name, description or None)
    typer.echo(f"Created suite [{suite_id}]: {name}")


@suites_app.command("delete")
def suites_delete(suite_id: int = typer.Argument(...)):
    init_db()
    suite = get_suite(suite_id)
    if not suite:
        typer.echo(f"Suite {suite_id} not found.", err=True)
        raise typer.Exit(1)
    delete_suite(suite_id)
    typer.echo(f"Deleted suite [{suite_id}]: {suite['name']}")
