# PromptOps

> **Prompt-as-code MLOps framework** — version, evaluate, optimize, and monitor LLM prompts with the same rigor applied to software.

Live demo → [promptopsframework-production-a54a.up.railway.app](https://promptopsframework-production-a54a.up.railway.app)
Backend API → [promptopsframework-production.up.railway.app/docs](https://promptopsframework-production.up.railway.app/docs)

---

## The Problem

Prompt engineering happens in notebooks, chat windows, and scattered scripts. There's no versioning, no systematic evaluation, no way to know if a change made things better or worse. PromptOps fixes that.

---

## What It Does

| Capability | Details |
|---|---|
| **Prompt versioning** | SHA-256 hash of every prompt config — detect duplicates, track changes |
| **Automated evaluation** | LLM-as-judge scores outputs across custom rubric criteria (3× parallel calls averaged for stability) |
| **Multi-metric objective** | `quality − token_penalty − format_penalty − latency_penalty` |
| **Regression detection** | Every run compared against previous best — warns and badges if quality drops |
| **Automatic optimization** | 7-8 mutations + LLM rewriter evaluated in parallel → greedy best-of-N with early stopping |
| **A/B testing** | Side-by-side prompt comparison with word-level diff |
| **Test suites** | Persistent named collections of test cases with expected outputs and rubrics |
| **Experiment tracking** | MLflow logs params, metrics, and output artifacts for every run |
| **Multi-provider** | Ollama (local), OpenAI, Anthropic — swap via a single `provider` field |

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│              Next.js 14 Frontend                     │
│  Dashboard · Playground · Optimizer · Suites        │
└──────────────────────┬──────────────────────────────┘
                       │ REST
┌──────────────────────▼──────────────────────────────┐
│              FastAPI Backend                         │
│  /run · /preview · /optimize · /health · /suites    │
└──────┬───────────────┬──────────────────────────────┘
       │               │
┌──────▼──────┐  ┌─────▼──────────────────────────────┐
│   SQLite    │  │         Adapter Layer               │
│  runs       │  │  OllamaAdapter · OpenAIAdapter      │
│  run_results│  │  AnthropicAdapter                  │
│  suites     │  │  make_adapter(provider)             │
│  suite_cases│  └─────┬──────────────────────────────┘
└─────────────┘        │
                ┌──────▼──────┐
                │   MLflow    │
                │  params +   │
                │  metrics +  │
                │  artifacts  │
                └─────────────┘
```

### Core Data Flow (single run)

1. `run_dataset()` — health-checks the provider, opens an MLflow run
2. All test cases evaluated **in parallel** via `asyncio.gather`
3. Each case: render template → generate output → judge 3× → average scores → compute objective
4. Regression check against previous best for the same prompt
5. Results written to SQLite (`runs` + `run_results` tables) and MLflow

---

## Tech Stack

**Backend** — Python 3.11, FastAPI, Pydantic v2, SQLite, MLflow, httpx (async), Typer CLI
**Frontend** — Next.js 14, React 18, Tailwind CSS
**Providers** — Ollama (local LLMs), OpenAI API, Anthropic API
**Infra** — Docker, Docker Compose, Railway (CI/CD via GitHub push)

---

## Key Design Decisions

**Why LLM-as-judge?**
Human evaluation doesn't scale. An LLM judge with a structured rubric gives reproducible, multi-criterion scores that correlate well with human preference — at scale.

**Why 3× judge calls averaged?**
LLM outputs at temperature > 0 are non-deterministic. Averaging 3 concurrent calls cuts variance significantly without tripling wall-clock time (they run in parallel).

**Why a multi-metric objective?**
Raw judge score ignores real costs. The objective penalizes token waste, format failures, and latency — prompts that are both high quality *and* efficient score better.

**Why parallel candidate evaluation?**
The optimization loop generates 7-8 mutations + an LLM rewrite. Sequential eval would be impractical. With `asyncio.gather`, all candidates run simultaneously.

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

### Regression Detection

Every run stores `avg_objective` in SQLite. On the next run of the same prompt, the system queries the previous best and compares. If the new score is lower: warning printed to stderr, `regression=1` stored in DB, red "↓ Regression" badge shown in the dashboard.

### Test Suites

Named, persistent collections of test cases (input + expected output + rubric). Run any prompt against a suite via `POST /run` with `suite_id`. Managed from the UI or CLI.

---

## Screenshots

| Dashboard | Playground | Optimizer |
|---|---|---|
| Live KPIs, trend chart, regression badges, auto-refresh | A/B comparison, diff view, provider select | Best prompt display, criteria scores |

---

## Quickstart

### Local (with Ollama)

```bash
# 1. Start Ollama
ollama serve && ollama pull llama3.1

# 2. Backend
pip install -e .
uvicorn promptops.api.app:app --reload --port 8000

# 3. Frontend
cd frontend && npm install && npm run dev

# 4. MLflow UI (optional)
mlflow ui
```

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
| `CORS_ORIGINS` | `http://localhost:3000` | Allowed frontend origins |
| `PROMPTOPS_DB` | `./promptops.db` | SQLite path |
| `NEXT_PUBLIC_API_URL` | `http://127.0.0.1:8000` | Backend URL (baked at build time) |

---

## Project Structure

```
promptops/
├── core/
│   ├── prompt.py          # Prompt model (name, system, template, provider…)
│   ├── runner.py          # run_dataset(), run_prompt(), regression detection
│   └── adapters/          # BaseAdapter, OllamaAdapter, OpenAIAdapter, AnthropicAdapter
├── eval/
│   ├── judge.py           # LLM-as-judge, 3× stability, multi-criterion
│   └── metrics.py         # compute_metrics(), objective formula
├── opt/
│   ├── mutations.py       # 7-8 deterministic prompt variants
│   ├── rewriter.py        # LLM-driven rewrite with feedback context
│   └── optimizer.py       # Parallel eval, greedy selection, early stopping
├── store/
│   └── db.py              # SQLite schema + all query functions
├── api/
│   └── app.py             # FastAPI — all endpoints
└── cli.py                 # Typer CLI

frontend/src/app/
├── page.tsx               # Dashboard (server-side + auto-refresh client)
├── playground/page.tsx    # A/B testing, diff view, Save Run
├── optimize/page.tsx      # Optimizer UI
├── suites/page.tsx        # Suite management
└── runs/[id]/page.tsx     # Run detail + per-case breakdown
```
