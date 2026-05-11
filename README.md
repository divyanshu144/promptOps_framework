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
| **Streaming optimizer** | `/optimize/stream` SSE endpoint — watch candidates score in real time |
| **A/B testing** | Side-by-side prompt comparison with word-level diff |
| **Test suites** | Persistent named collections of test cases with expected outputs and rubrics |
| **Prompt history** | Per-prompt run history with aggregate stats and trend view |
| **Experiment tracking** | MLflow logs params, metrics, and output artifacts for every run |
| **Multi-provider** | Ollama (local), OpenAI, Anthropic — swap via a single `provider` field |

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
3. Each case: render template → generate output → judge 3× → average scores → compute objective
4. Regression check against previous best for the same prompt
5. Results written to SQLite (`runs` + `run_results` tables) and MLflow

---

## Tech Stack

**Backend** — Python 3.11, FastAPI, Pydantic v2, SQLite, MLflow, httpx (async), Typer CLI  
**Frontend** — Next.js 14, React 18, Tailwind CSS, Outfit + DM Mono fonts  
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

The `/optimize/stream` endpoint streams each candidate's score as a server-sent event so the UI can show a live terminal-style progress log.

### Regression Detection

Every run stores `avg_objective` in SQLite. On the next run of the same prompt, the system queries the previous best and compares. If the new score is lower: warning printed to stderr, `regression=1` stored in DB, red "↓ Regression" badge shown in the dashboard.

### Test Suites

Named, persistent collections of test cases (input + expected output + rubric). Run any prompt against a suite via `POST /run` with `suite_id`. Managed from the UI or CLI.

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
│   └── adapters/          # BaseAdapter, OllamaAdapter, OpenAIAdapter, AnthropicAdapter
├── eval/
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
│   └── ...                # pytest suite (33 tests covering core, eval, opt, store)
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

All 33 tests run without a live model provider — they use mocked adapters.

---

## Adding a New Provider

1. Create `promptops/core/adapters/myprovider.py` extending `BaseAdapter`
2. Implement `generate()` and `health_check()`
3. Register in `make_adapter()` in `promptops/core/adapters/__init__.py`
4. Add the provider name to the select dropdowns in `playground/page.tsx` and `optimize/page.tsx`

---

## Deployment (Railway)

- **Backend**: `railway.toml` at root — Dockerfile builder, `sh -c 'uvicorn ... --port $PORT'`
- **Frontend**: `frontend/railway.toml` — Nixpacks builder, `sh -c 'next start -p $PORT'`
- Push to `main` → Railway auto-deploys both services
- No Ollama on Railway — set `OPENAI_API_KEY` and use `provider=openai`
