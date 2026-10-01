# PromptOps

> **LLM evaluation and prompt observability platform** — evaluate prompt and RAG quality, detect regressions, enforce CI quality gates, and inspect failures through FastAPI, Next.js, SQLite, and MLflow.

Run offline regression demos without model API keys; connect Ollama, OpenAI, Claude, or Mistral for live evaluations.


---

## The Problem

Prompt engineering happens in notebooks, chat windows, and scattered scripts. There's no versioning, no systematic evaluation, no way to know if a change made things better or worse. PromptOps fixes that.

---

## What It Does

| Capability | Details |
|---|---|
| **Prompt versioning** | SHA-256 hash of every prompt config — detect duplicates, track changes |
| **Pluggable eval harness** | Swap evaluation strategies via `EvalHarness` ABC — built-in LLM judge or DeepEval (G-Eval + AnswerRelevancy); routes through your existing model provider, no new API keys |
| **Automated evaluation** | LLM-as-judge scores outputs across custom rubric criteria (3× parallel calls averaged for stability) |
| **Multi-metric objective** | `quality − token_penalty − format_penalty − latency_penalty` |
| **Regression detection** | Every run compared against previous best — warns and badges if quality drops |
| **Automatic optimization** | 7-8 mutations + LLM rewriter evaluated in parallel → greedy best-of-N with early stopping |
| **Streaming optimizer** | `/optimize/stream` SSE endpoint — watch candidates score in real time |
| **A/B testing** | Side-by-side prompt comparison with word-level diff |
| **Pass-rate tracking** | Per-case pass/fail threshold → `pass_rate` aggregated per run, stored in DB, shown on dashboard |
| **Test suites** | Persistent named collections of test cases with expected outputs and rubrics |
| **Prompt history** | Per-prompt run history with aggregate stats and trend view |
| **Experiment tracking** | MLflow logs params, metrics, and output artifacts for every run |
| **Multi-provider** | Ollama (local), OpenAI, Claude, Mistral — swap via a single `provider` field |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Next.js 14 Frontend                           │
│  Dashboard · Playground · Optimizer · Suites · Prompt History   │
└──────────────────────────┬──────────────────────────────────────┘
                           │ REST / SSE
┌──────────────────────────▼──────────────────────────────────────┐
│                      FastAPI Backend                             │
│  /run · /preview · /optimize · /optimize/stream · /health       │
│  /suites · /prompts · /runs · /leaderboard                      │
└──────┬────────────────────┬───────────────────────────────────--┘
       │                    │
┌──────▼──────┐  ┌──────────▼─────────────────────────────────────┐
│   SQLite    │  │              Adapter Layer                       │
│  runs       │  │  OllamaAdapter · OpenAIAdapter · AnthropicAdapter│
│  run_results│  │  make_adapter(provider)                          │
│  suites     │  └──────────┬─────────────────────────────────────-┘
│  suite_cases│             │
└─────────────┘      ┌──────▼──────┐
                     │   MLflow    │
                     │  params +   │
                     │  metrics +  │
                     │  artifacts  │
                     └─────────────┘
```

### Core Data Flow (single run)

1. `run_dataset()` — health-checks the provider, opens an MLflow run
2. All test cases evaluated **in parallel** via `asyncio.gather`
3. Each case: render template → generate output → `harness.evaluate()` → compute objective → check `judge_score >= threshold` → `passed` flag
4. Regression check against previous best for the same prompt
5. `pass_rate` (% of cases that passed) aggregated, logged to MLflow, stored in SQLite
6. Results written to SQLite (`runs` + `run_results` tables) and MLflow

---

## Tech Stack

**Backend** — Python 3.11, FastAPI, Pydantic v2, SQLite, MLflow, httpx (async), Typer CLI  
**Frontend** — Next.js 14, React 18, Tailwind CSS, Outfit + DM Mono fonts  
**Providers** — Ollama (local LLMs), OpenAI API, Anthropic Claude API, Mistral API
**Infra** — Docker, Docker Compose, Railway (CI/CD via GitHub push)

---

## Key Design Decisions

**Why LLM-as-judge?**
Human evaluation doesn't scale. An LLM judge with a structured rubric gives reproducible, multi-criterion scores that correlate well with human preference — at scale.

**Why 3× judge calls averaged?**
LLM outputs at temperature > 0 are non-deterministic. Averaging 3 concurrent calls cuts variance significantly without tripling wall-clock time (they run in parallel).

**Why a multi-metric objective?**
Raw judge score ignores real costs. The objective penalizes token waste, format failures, and latency — prompts that are both high quality *and* efficient score better.

**Why a pluggable `EvalHarness`?**
The LLM-as-judge pattern is custom and unvalidated against the broader industry. The `EvalHarness` ABC decouples evaluation strategy from the rest of the pipeline — `LLMJudgeHarness` (the default) wraps the existing judge unchanged, while `DeepEvalHarness` wires in DeepEval's G-Eval and AnswerRelevancy metrics. Both return the same `JudgeResult` shape, so nothing downstream changes. New frameworks (RAGAS, Braintrust) can be added as additional harness implementations.

**Why parallel candidate evaluation?**
The optimization loop generates 7-8 mutations + an LLM rewrite. Sequential eval would be impractical. With `asyncio.gather`, all candidates run simultaneously.

**Why pass-rate alongside the objective?**
The objective is a continuous score good for driving the optimizer — small improvements are visible even when no new cases start passing. Pass-rate is binary (clear the threshold or not) and more interpretable for communicating quality: "we went from 60% → 80% on our golden set across 3 optimizer iterations." Both are tracked: objective guides the optimizer; pass-rate tells the story.

**Why SQLite over Postgres?**
Zero-ops, single-file, portable. MLflow handles the metrics/artifact store. SQLite handles structured queries (leaderboard, per-case breakdown, suite management) with no infra overhead.

---

## Features In Depth

### Optimization Loop

```
Base prompt → evaluate → score
     ↓
Generate candidates (parallel):
  _concise   · _format   · _json  · _bullets
  _finalonly · _fewshot  · _schema · _lowtokens
  + LLM rewrite (with current score + judge feedback as context)
     ↓
Evaluate all candidates in parallel
     ↓
Pick best → early stop if Δobjective < 0.005
     ↓
Repeat for N iterations
```

The `/optimize/stream` endpoint streams each candidate's score as a server-sent event so the UI can show a live terminal-style progress log.

### Regression Detection

Every run stores `avg_objective` in SQLite. On the next run of the same prompt, the system queries the previous best and compares. If the new score is lower: warning printed to stderr, `regression=1` stored in DB, red "↓ Regression" badge shown in the dashboard.

### Test Suites

Named, persistent collections of test cases (input + expected output + rubric). Run any prompt against a suite via `POST /run` with `suite_id`. Managed from the UI or CLI.

### Eval Harness

The evaluation strategy is pluggable via the `EvalHarness` ABC in `promptops/eval/harness.py`.

| Harness | How to use | What it does |
|---|---|---|
| `LLMJudgeHarness` | default (omit `eval_harness`) | 3× parallel LLM judge calls averaged; respects test-case rubric |
| `DeepEvalHarness` | `"eval_harness": "deepeval"` in `/run` body | DeepEval G-Eval + AnswerRelevancy via `PromptOpsDeepEvalLLM` bridge |

The `PromptOpsDeepEvalLLM` bridge routes all DeepEval metric calls through the existing `BaseAdapter`, so DeepEval works with Ollama, OpenAI, Claude, or Mistral — no extra API key.

To run the DeepEval-backed integration eval suite (requires Ollama):

```bash
pytest -m deepeval promptops/tests/evals/ -v
```

To add a new eval framework: implement `EvalHarness.evaluate()`, register it in the `/run` endpoint's `eval_harness` guard.

### Pass-Rate Tracking

Each `TestCase` carries a `threshold` (default `0.7`). After the judge scores an output, `passed = judge_score >= threshold`. At the end of each run:

- `pass_rate = passed_count / total_cases` is stored in the `runs` table and logged to MLflow
- Per-case `passed` (0/1) is stored in `run_results`
- Dashboard shows a **Best Pass Rate** KPI card and a Pass Rate column in the runs table
- Run detail shows a green **✓ pass** / red **✗ fail** badge on every case row

Suite cases store their own `threshold` so a golden set can have per-case pass bars. The objective still drives the optimizer (continuous signal); pass-rate is the human-readable quality story.

### Prompt History

The `/prompts` page lists every unique prompt name with run count, best objective, average objective, and timestamp of the last run. Click any row to drill into its full run history.

---

## Quickstart

### Local (with Ollama)

```bash
# 1. Start Ollama
ollama serve && ollama pull llama3.1

# 2. Backend (use an absolute path for the DB to avoid path ambiguity)
pip install -e .
PROMPTOPS_DB=/absolute/path/to/promptops.db uvicorn promptops.api.app:app --reload --port 8000

# 3. Frontend
cd frontend && npm install && npm run dev

# 4. MLflow UI (optional)
mlflow ui --port 5001
```

Open **http://localhost:3000** for the dashboard.

> **Note on `PROMPTOPS_DB`:** Always use an absolute path when running with `--reload`. Uvicorn's file-watcher spawns a child process whose working directory may differ from the parent, causing relative paths to resolve to different files.

### Docker

```bash
docker compose up --build
# Frontend:  http://localhost:3000
# Backend:   http://localhost:8000
# MLflow:    http://localhost:5001
```

### CLI

```bash
promptops run --provider ollama --model llama3.1
promptops optimize --iterations 3 --provider openai
promptops suites list
promptops suites create "regression-suite" --description "Core quality cases"
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_URL` | `http://localhost:11434` | Ollama server |
| `OPENAI_API_KEY` | — | For `provider=openai` |
| `ANTHROPIC_API_KEY` | — | For `provider=anthropic` |
| `MISTRAL_API_KEY` | — | For `provider=mistral` |
| `CORS_ORIGINS` | `http://localhost:3000` | Allowed frontend origins |
| `PROMPTOPS_DB` | `./promptops.db` | SQLite path — use absolute path locally |
| `MLFLOW_TRACKING_URI` | `./mlruns` | MLflow tracking dir or server URL |
| `NEXT_PUBLIC_API_URL` | `http://127.0.0.1:8000` | Backend URL (baked at Next.js build time) |
| `NEXT_PUBLIC_MLFLOW_URL` | `http://localhost:5001` | MLflow URL for run links in the UI |

---

## Project Structure

```
promptops/
├── core/
│   ├── prompt.py          # Prompt model (name, system, template, provider…)
│   ├── runner.py          # run_dataset(), run_prompt(), regression detection
│   └── adapters/          # BaseAdapter, OllamaAdapter, OpenAIAdapter, AnthropicAdapter, MistralAdapter
├── eval/
│   ├── harness.py         # EvalHarness ABC — pluggable evaluation interface
│   ├── llm_judge_harness.py  # LLMJudgeHarness — default, wraps judge.py
│   ├── deepeval_harness.py   # DeepEvalHarness + PromptOpsDeepEvalLLM bridge
│   ├── judge.py           # LLM-as-judge, 3× stability averaging, multi-criterion
│   └── metrics.py         # compute_metrics(), objective formula
├── opt/
│   ├── mutations.py       # 7-8 deterministic prompt variants (incl. few-shot)
│   ├── rewriter.py        # LLM-driven rewrite with score + judge feedback context
│   └── optimizer.py       # Parallel eval, greedy selection, early stopping
├── store/
│   └── db.py              # SQLite schema + all query functions
├── api/
│   └── app.py             # FastAPI — all endpoints including /optimize/stream SSE
├── tests/
│   └── ...                # pytest suite covering core, eval, opt, store, CI gates, and RAG
└── tests/evals/           # DeepEval integration tests (require Ollama; skips if unavailable)
└── cli.py                 # Typer CLI

frontend/src/app/
├── page.tsx               # Dashboard (server-side fetch → DashboardClient)
├── components/
│   ├── DashboardClient.tsx  # Live KPIs, trend sparkline, regression badges, 10s auto-refresh
│   └── NavBar.tsx           # Sticky nav, animated logo, active link pills
├── playground/page.tsx    # A/B testing, word-level diff, provider select, Save Run
├── optimize/page.tsx      # Optimizer UI — terminal-style streaming log
├── suites/page.tsx        # Suite management (create, delete, add/remove cases)
├── prompts/page.tsx       # Prompt history — aggregate stats per prompt name
└── runs/[id]/page.tsx     # Run detail + per-case breakdown + MLflow link
```

---

## Running Tests

```bash
pytest tests/ -v
```

Normal tests run offline with mocked adapters and explicit response fixtures.

```bash
# Integration tests (require Ollama running)
pytest -m deepeval promptops/tests/evals/ -v
```

---

## Adding a New Provider

1. Create `promptops/core/adapters/myprovider.py` extending `BaseAdapter`
2. Implement `generate()` and `health_check()`
3. Register in `make_adapter()` in `promptops/core/adapters/__init__.py`
4. Add the provider name to the select dropdowns in `playground/page.tsx` and `optimize/page.tsx`

---

## Adding a New Eval Framework

1. Create `promptops/eval/myframework_harness.py` implementing `EvalHarness`
2. Implement `async evaluate(user_input, actual_output, expected_output, rubric) -> JudgeResult`
3. Register a new string key in the `eval_harness` guard in `promptops/api/app.py`

The `JudgeResult` shape (`score`, `criteria`, `reasoning`) is what the rest of the pipeline consumes — as long as your harness returns that, nothing else changes.

---

## Deployment (Railway)

- **Backend**: `railway.toml` at root — Dockerfile builder, `sh -c 'uvicorn ... --port $PORT'`
- **Frontend**: `frontend/railway.toml` — Nixpacks builder, `sh -c 'next start -p $PORT'`
- Push to `main` → Railway auto-deploys both services
- No Ollama on Railway — set `OPENAI_API_KEY` and use `provider=openai`


## Production AI Engineering

This project demonstrates evaluation harness design, regression detection, CI quality gates,
RAG groundedness diagnostics, failure analysis, MLflow experiment tracking, and multi-provider
integration. Prompt optimization is one workflow within the evaluation and observability platform.
The local architecture is suited to development and evaluation workloads; authentication,
queueing, distributed storage, and deployment hardening remain separate production concerns.

## CI Quality Gate

```bash
promptops ci --suite regression-suite --prompt path/to/prompt.json --min-pass-rate 0.85
# Stored suite IDs also work; suites can instead be JSON files containing a cases array.
promptops ci --suite examples/rag/suite.json --prompt optimized --harness rag \
  --replay examples/rag/optimized-responses.json --min-pass-rate 0.85
```

`--prompt` accepts a JSON Prompt config or an example name (`baseline`, `optimized`, resolved
relative to the repository's `examples/rag` directory). `--suite` accepts a stored name/ID or JSON file.
The command runs the existing runner, logs to MLflow, saves per-case results to SQLite, prints
pass rate and average objective, and stores gate status. Exit codes: **0 passed, 1 threshold
failed, 2 invalid input/provider error**. Empty suites fail. The threshold is inclusive.
Use `--judge-provider` and `--judge-model` to configure a separate judge for generic evaluations.
`MLFLOW_TRACKING_URI` controls CLI tracking. See [offline workflow](.github/workflows/promptops-quality.yml).
Without `--replay`, generation uses the provider/model in the prompt JSON; live demos require
Ollama or optional API credentials. Replay is explicitly fixture-based and only supported with RAG.
The existing `release-gate` command checks an already-stored run against multiple metric limits.

## RAG Evaluation and Failure Analysis

Select `"eval_harness": "rag"` in `POST /run` or `--harness rag` in the CLI.
Case `input` contains `question`, `contexts: [{"id": "policy", "text": "..."}]`, and
`expected_citations: ["policy"]`; `expected` contains the golden answer. Existing suite CRUD
persists these inputs without a schema migration. See [sample suite](examples/rag/suite.json).

`RAGHarness` implements the existing `EvalHarness` interface. It reports faithfulness/groundedness,
context relevance (expected-source precision), citation coverage, unsupported-claim rate, and
answer relevance (golden-answer token recall). Quality is the minimum of faithfulness, citation
coverage, and answer relevance, so one strong metric cannot hide an unsupported answer.
Per-case metrics and run aggregates are persisted and logged to MLflow.

These are **lexical extractive diagnostics**, not semantic fact verification. Claims are split
on sentence boundaries/newlines and must match a contiguous source phrase; bracketed
citations must refer to supplied source IDs. Paraphrases, negation, and complex claims can be
mis-scored. Use a semantic `EvalHarness` and human-reviewed golden sets for broader RAG workloads.
Context relevance uses annotated source IDs, rather than a semantic relevance model.

Failed cases receive evidence-based labels: `hallucination`, `missing_citation`,
`format_violation`, `incomplete_answer`, `wrong_or_irrelevant_answer`, and `unsafe_output`.
Safety labels require a judge-provided `safety` criterion; there is no built-in safety detector.
Explicit `rubric.budgets` (`max_output_words`, `max_latency_ms`, `max_cost_usd`) add `verbosity`,
`latency_regression`, and `cost_regression`. Budget labels compare with absolute case limits.
Failures without specific evidence are `unclassified`. Labels are diagnostic hypotheses.
Budget violations fail the case and affect the CI pass rate; a required latency/cost metric
that is unavailable also fails the case. JSON output schemas are validated, rather than only
checking whether the output parses. They live in the existing result metrics JSON and appear as `failure_labels` in
`GET /runs/{id}` and badges in the run detail UI. Legacy results return an empty label list.
All three live adapters can estimate generation cost from explicitly configured token prices.
Set `PROMPTOPS_TOKEN_PRICES` to a JSON mapping of `"provider:model"` to `{"input": 2, "output": 4}`
with your effective USD-per-million-token rates. No pricing is hardcoded. Costs are tagged as
configured estimates; missing usage or rates stays unknown. Use effective rates appropriate
to your cache/billing arrangement; estimates cover generation, not judge calls or provider invoices. The existing objective penalizes tokens and latency.

## Case Study: Grounded Support Answers

A four-case support-policy suite compares a generic baseline prompt with a source-only,
citation-required prompt. [Reproduce the benchmark](docs/case-study.md) offline or use the same
prompt pair with a live provider. These are **illustrative fixture results**, not measured model gains.

| Metric | Baseline | Optimized |
|---|---:|---:|
| Pass rate | 25% | 100% |
| Average objective | 0.1590 | 0.9455 |
| Average generation tokens | 150 | 130 |
| Fixture cost per attempted task | $0.0003 | $0.0002 |
| Fixture generation latency p50/p95 | 800 ms | 450 ms |
| Failure labels | hallucination, missing citation, incomplete answer, wrong or irrelevant answer | none |

A separate [measured local benchmark](docs/case-study.md#measured-local-benchmark--october-1-2026)
ran Llama 3.1 with a Qwen semantic judge over three alternating repeats: **0% → 100% citation-compliant
answers**, with total tokens increasing from 64.50 to 134.25 per answer. This is a small four-case
measurement; the full report includes latency and raw outputs.

Outputs, token counts, costs, and latencies in the table above are authored fixtures; the real evaluation/scoring,
SQLite persistence, and MLflow path run end to end. Replay reports fixture latency rather than
local execution time. Live results vary and include additional judge overhead where applicable.


### Semantic RAG Evaluation

For paraphrased answers and complex claims, use the provider-backed semantic harness:

```bash
promptops ci --suite examples/rag/suite.json --prompt optimized \
  --harness rag-semantic --judge-provider ollama --judge-model llama3.1
```

API callers select `"eval_harness": "rag-semantic"`. The semantic judge scores faithfulness,
context relevance, answer relevance, completeness, citation support, and safety. It receives
sources and the golden answer as untrusted data, with strict score validation. Invalid/missing
scores fail closed; independent source-ID checks prevent the judge accepting invented or
missing citations. Normal tests mock these model calls, and the offline replay demo remains
extractive. Semantic judges still require calibrated golden sets and human review; their
judgments are model estimates, not guarantees of truth.

### Release Gate Configuration

Default stored-run release gates require universally available metrics: task success ≥90%,
latency p95 ≤8 seconds, and at most a 2-point task-success drop if a baseline is supplied.
Tool/retrieval metrics are enforced when explicitly configured, so generic prompts no longer
fail solely because they have no retrieval or tool calls. Every configured metric must exist,
including baseline comparison metrics; nonfinite scores fail closed.

```bash
promptops release-gate 12 --thresholds examples/rag/release-thresholds.json --baseline-run-id 10
```

API callers can supply the same object as `gate_thresholds` to `/run`, or `thresholds` to
`POST /runs/{id}/release-gate`. Run details display gate status and aggregate evaluation metrics.
Generic quality scores are no longer reported as groundedness/hallucination measurements;
those metrics require a judge's explicit grounding criterion.

### Cloud providers

Copy `.env.example` to `.env` in the project root and fill in the keys you need.
The CLI and API load this file when started from the project root; restart the API after editing it.
Existing environment variables take precedence. `.env` is ignored by Git.
Configure credentials on the backend or CLI host; keys are never entered into the browser.
Docker Compose forwards these environment variables to the backend.

| Provider | Environment variable | Default CLI/UI model |
| --- | --- | --- |
| OpenAI (`openai`) | `OPENAI_API_KEY` | `gpt-4o-mini` |
| Claude (`anthropic`, CLI alias `claude`) | `ANTHROPIC_API_KEY` | `claude-haiku-4-5-20251001` |
| Mistral (`mistral`) | `MISTRAL_API_KEY` | `mistral-small-latest` |

Choose a provider in Playground or Optimize; switching providers selects a compatible default model, which you can override. The judge can use a different provider. CLI example:

```bash
promptops run --provider mistral --judge-provider openai
```

For CI, set `provider` and `model` in the prompt JSON (see `examples/providers/`),
then use that file with `promptops ci --suite examples/rag/suite.json --prompt examples/providers/mistral.json --min-pass-rate 0.85`.
Live generation and semantic judges incur provider charges; normal tests and replay demos stay offline.
Mistral uses its [OpenAI-compatible API](https://docs.mistral.ai/resources/migration-guides) through the existing OpenAI SDK.
Cost estimates remain configurable through `PROMPTOPS_TOKEN_PRICES`; unknown prices are reported as unknown.
