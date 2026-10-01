from __future__ import annotations

import asyncio
import sys
import json
import os
from pathlib import Path

import typer
from dotenv import load_dotenv

# Read local configuration before modules capture database/tracking settings.
# Explicit environment variables always take precedence.
load_dotenv(dotenv_path=".env", override=False)

from promptops.core.adapters import make_adapter, default_model
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
    get_run,
    get_run_results,
    update_run_gate,
)
from promptops.eval.release import evaluate_release_gate

app = typer.Typer(add_completion=False)
suites_app = typer.Typer()
app.add_typer(suites_app, name="suites")


@app.command()
def run(
    model: str | None = None,
    judge_model: str | None = None,
    provider: str = "ollama",
    judge_provider: str | None = typer.Option(
        None,
        "--judge-provider",
        help="Provider for the judge model, if different from --provider (enables "
        "cross-provider judging so the judge isn't the same model evaluating itself).",
    ),
):
    model = model or default_model(provider)
    judge_model = judge_model or (default_model(judge_provider) if judge_provider else model)
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
        judge_adapter = make_adapter(judge_provider) if judge_provider else None
        results = await run_dataset(
            adapter, prompt, demo_dataset(), judge_model, judge_adapter=judge_adapter
        )
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

    typer.echo(f"Eval metrics: {results.get('aggregate_metrics')}")
    typer.echo(results)


@app.command("release-gate")
def release_gate(
    run_id: int = typer.Argument(...),
    baseline_run_id: int | None = typer.Option(None, "--baseline-run-id"),
    thresholds: Path | None = typer.Option(None, help="JSON release threshold configuration"),
):
    init_db()
    run_row = get_run(run_id)
    if not run_row:
        typer.echo(f"Run {run_id} not found.", err=True)
        raise typer.Exit(1)
    baseline = get_run(baseline_run_id) if baseline_run_id is not None else None
    if baseline_run_id is not None and baseline is None:
        typer.echo(f"Baseline run {baseline_run_id} not found.", err=True)
        raise typer.Exit(1)
    from promptops.eval.release import ReleaseGateThresholds
    try:
        config = ReleaseGateThresholds.model_validate_json(thresholds.read_text()) if thresholds else None
    except (ValueError, OSError) as exc:
        typer.echo(f"Invalid thresholds: {exc}", err=True)
        raise typer.Exit(2)
    result = evaluate_release_gate(
        run_row.get("aggregate_metrics"),
        thresholds=config,
        baseline_metrics=baseline.get("aggregate_metrics") if baseline else None,
    )
    update_run_gate(run_id, "passed" if result.passed else "failed")
    typer.echo(result.model_dump())
    if not result.passed:
        raise typer.Exit(1)


@app.command()
def optimize(
    model: str | None = None,
    judge_model: str | None = None,
    iterations: int = 2,
    use_rewriter: bool = True,
    rewriter_model: str | None = None,
    provider: str = "ollama",
    repeats: int = typer.Option(1, "--repeats", help="Re-run each candidate this many times and average, to separate real prompt improvement from generation sampling noise."),
    judge_provider: str | None = typer.Option(
        None,
        "--judge-provider",
        help="Provider for the judge model, if different from --provider (enables "
        "cross-provider judging so the judge isn't the same model evaluating itself).",
    ),
):
    model = model or default_model(provider)
    judge_model = judge_model or (default_model(judge_provider) if judge_provider else model)
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
        judge_adapter = make_adapter(judge_provider) if judge_provider else None
        results = await optimize_prompt(
            adapter,
            prompt,
            demo_dataset(),
            judge_model,
            iterations,
            use_rewriter,
            rewriter_model,
            repeats=repeats,
            judge_adapter=judge_adapter,
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


@app.command()
def ci(
    suite: str = typer.Option(..., "--suite", help="Stored suite name/ID or JSON file"),
    prompt: str = typer.Option(..., "--prompt", help="Prompt JSON file or example name"),
    min_pass_rate: float = typer.Option(0.85, min=0.0, max=1.0),
    harness: str = typer.Option("llm_judge", help="llm_judge, rag (extractive), or rag-semantic"),
    judge_model: str | None = None,
    judge_provider: str | None = None,
    replay: Path | None = typer.Option(None, help="Explicit offline response fixture file"),
):
    """Evaluate a suite, persist results, and exit 1 when the quality gate fails."""
    from promptops.eval.rag_harness import RAGHarness, SemanticRAGHarness
    from promptops.tests.testcase import TestCase
    from promptops.store.db import get_suite_cases
    from promptops.core.adapters.replay import ReplayAdapter

    init_db()
    try:
        if harness not in {"llm_judge", "rag", "rag-semantic"}:
            raise ValueError("Harness must be llm_judge, rag, or rag-semantic")
        prompt_path = Path(prompt)
        if not prompt_path.is_file():
            prompt_path = Path("examples/rag") / f"{prompt}.json"
        config = Prompt.model_validate_json(prompt_path.read_text())
        judge_model = judge_model or (default_model(judge_provider) if judge_provider else config.model)
        suite_id = None
        suite_path = Path(suite)
        if suite_path.is_file():
            cases = json.loads(suite_path.read_text())["cases"]
        else:
            stored = next((s for s in list_suites() if s["name"] == suite or str(s["id"]) == suite), None)
            if stored is None:
                raise ValueError(f"Suite {suite!r} not found")
            suite_id = stored["id"]
            cases = get_suite_cases(suite_id)
        fields = {"input", "expected", "rubric", "threshold", "expected_tools", "relevant_doc_ids", "expected_claims"}
        testcases = [TestCase(**{k: v for k, v in c.items() if k in fields}) for c in cases]
        if not testcases:
            raise ValueError("Suite has no cases")
        if replay is not None and harness != "rag":
            raise ValueError("Offline replay requires --harness rag")
        adapter = ReplayAdapter(json.loads(replay.read_text())) if replay else make_adapter(config.provider)
        judge_adapter = make_adapter(judge_provider) if judge_provider else None
        result = asyncio.run(run_dataset(
            adapter, config, testcases, judge_model,
            harness=(RAGHarness() if harness == "rag" else
                     SemanticRAGHarness(judge_adapter or adapter, judge_model) if harness == "rag-semantic" else None),
            suite_id=suite_id, eval_harness_name=harness,
            mlflow_uri=os.getenv("MLFLOW_TRACKING_URI", "./mlruns"),
            judge_adapter=judge_adapter,
        ))
    except Exception as exc:
        typer.echo(f"CI ERROR: {exc}", err=True)
        raise typer.Exit(2)
    passed = result["pass_rate"] >= min_pass_rate
    update_run_gate(result["run_id"], "passed" if passed else "failed")
    typer.echo(f"CI {'PASS' if passed else 'FAIL'} | run={result['run_id']} | cases={len(testcases)}")
    typer.echo(f"Pass rate: {result['pass_rate']:.1%} (required {min_pass_rate:.1%})")
    typer.echo(f"Average objective: {result['avg_objective']:.4f}")
    typer.echo(f"Average judge score: {result['avg_judge_score']:.4f}")
    rows = get_run_results(result["run_id"])
    labels = sorted({label for row in rows for label in row.get("failure_labels", [])})
    typer.echo(f"Failure labels: {', '.join(labels) if labels else 'none'}")
    aggregate = result.get("aggregate_metrics", {})
    typer.echo(f"Latency p95 (ms): {aggregate.get('latency_p95_ms', 'unknown')}")
    typer.echo(f"Cost per attempted task (USD): {aggregate.get('cost_per_attempted_task', 'unknown')}")
    if not passed:
        raise typer.Exit(1)
