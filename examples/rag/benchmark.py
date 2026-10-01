"""Reproduce the live local support benchmark; costs remain unknown without configured rates.

python examples/rag/benchmark.py --repeats 3 --output docs/validation/live-benchmark.json
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import platform
from datetime import datetime, timezone
from pathlib import Path


async def benchmark(args):
    from promptops.core.adapters.ollama import OllamaAdapter
    from promptops.core.prompt import Prompt
    from promptops.core.runner import run_dataset
    from promptops.eval.rag_harness import SemanticRAGHarness
    from promptops.store.db import get_run_results, update_run_gate
    from promptops.tests.testcase import TestCase

    directory = Path(__file__).resolve().parent
    suite_bytes = (directory / "suite.json").read_bytes()
    cases = [TestCase(**c) for c in json.loads(suite_bytes)["cases"]]
    prompts = {}
    for variant in ("baseline", "optimized"):
        config = json.loads((directory / f"{variant}.json").read_text())
        config["name"] = f"support_live_{variant}"
        config["model"] = args.model
        config["params"].update({"seed": 42, "num_ctx": 4096, "keep_alive": "30m"})
        prompts[variant] = Prompt(**config)
    adapter = OllamaAdapter(timeout_s=180)
    if not await adapter.health_check():
        raise RuntimeError("Start Ollama and ensure generation/judge models are installed")
    # Warm both models; every variant receives the same options and source data.
    for model in dict.fromkeys((args.model, args.judge_model)):
        await adapter.generate(model, "", "Say ready.", {"temperature": 0, "max_tokens": 2, "keep_alive": "30m", "num_ctx": 4096})
    report = {
        "kind": "live_local_models", "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "generation_model": args.model, "judge_model": args.judge_model,
        "platform": platform.system(), "architecture": platform.machine(),
        "suite_sha256": hashlib.sha256(suite_bytes).hexdigest(),
        "repeats": args.repeats, "case_count": len(cases), "case_concurrency": len(cases),
        "prompts": {k: v.model_dump() for k, v in prompts.items()}, "runs": [],
        "method": "Alternating variant order; warmed models; generation-only provider latency and token usage. Semantic judge via separate model. No price rates assumed.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    for repeat in range(args.repeats):
        order = ("baseline", "optimized") if repeat % 2 == 0 else ("optimized", "baseline")
        for variant in order:
            print(f"Repeat {repeat + 1}/{args.repeats}: {variant}", flush=True)
            result = await run_dataset(adapter, prompts[variant], cases, args.judge_model,
                harness=SemanticRAGHarness(adapter, args.judge_model), eval_harness_name="rag-semantic",
                release_label=f"live-repeat-{repeat + 1}")
            update_run_gate(result["run_id"], "passed" if result["pass_rate"] >= .85 else "failed")
            rows = get_run_results(result["run_id"])
            report["runs"].append({"variant": variant, "repeat": repeat + 1, **result,
                                   "cases": [{k: row[k] for k in ("test_idx", "input", "expected", "output", "judge_score", "judge_criteria", "judge_reasoning", "metrics", "passed", "failure_labels")} for row in rows]})
            args.output.write_text(json.dumps(report, indent=2) + "\n")
            print(f"  pass={result['pass_rate']:.0%} objective={result['avg_objective']:.4f}", flush=True)
    print(f"Saved {args.output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="llama3.1")
    parser.add_argument("--judge-model", default="qwen2.5:3b")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--output", type=Path, default=Path("docs/validation/live-benchmark.json"))
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be positive")
    asyncio.run(benchmark(args))
