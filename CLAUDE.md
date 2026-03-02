# PromptOps Framework

A **prompt-as-code MLOps framework** — version, evaluate, and systematically optimize LLM prompts the same way you manage software. Every prompt run is tracked, scored, compared, and stored for regression detection.

---

## What It Does

1. **Run** a prompt against a dataset → LLM-as-judge scores each output → objective metric computed → stored in SQLite + MLflow
2. **Optimize** → generate 7-8 mutations + LLM rewrite → evaluate all in parallel → pick best → early-stop if flat
3. **Detect regressions** → compare new run's objective vs previous best for same prompt name → warn + badge
4. **A/B test** in the Playground → side-by-side output comparison with word-level diff
5. **Manage test suites** → persistent named collections of test cases with expected outputs + rubrics

---

## Architecture

```
User (CLI / Frontend / API)
        ↓
  FastAPI (api/app.py)
        ↓
  make_adapter(provider)        ← OllamaAdapter | OpenAIAdapter | AnthropicAdapter
        ↓
  run_dataset() / optimize_prompt()
    ├── health_check()           ← abort early if provider unreachable
    ├── asyncio.gather(run_prompt per testcase)   ← parallel
    │     ├── adapter.generate()
    │     ├── judge_output() × 3  ← stability averaging
    │     └── compute_metrics()   ← objective formula
    ├── regression detection      ← compare vs previous best
    ├── insert_run() + insert_run_result()   ← SQLite
    └── mlflow.log_metric()       ← MLflow
```

---

## Key Files

| File | Purpose |
|---|---|
| `promptops/core/prompt.py` | `Prompt` model — name, system, template, model, params, provider |
| `promptops/core/adapters/__init__.py` | `make_adapter(provider)` factory |
| `promptops/core/adapters/base.py` | `BaseAdapter` ABC + `ModelResponse` |
| `promptops/core/adapters/ollama.py` | Ollama (local); maps `max_tokens`→`num_predict` |
| `promptops/core/adapters/openai.py` | OpenAI; reads `OPENAI_API_KEY` |
| `promptops/core/adapters/anthropic.py` | Anthropic; reads `ANTHROPIC_API_KEY` |
| `promptops/core/runner.py` | `run_dataset()`, `run_prompt()`, `run_prompt_detailed()` |
| `promptops/eval/judge.py` | LLM-as-judge; 3× parallel calls averaged; multi-criterion JSON |
| `promptops/eval/metrics.py` | `compute_metrics()` → `RunMetrics` with objective score |
| `promptops/opt/mutations.py` | `basic_mutations(prompt, testcases)` — 7-8 variants |
| `promptops/opt/rewriter.py` | LLM-driven rewrite with score/reasoning context |
| `promptops/opt/optimizer.py` | `optimize_prompt()` — parallel eval, early stopping |
| `promptops/store/db.py` | SQLite; all tables + query functions |
| `promptops/tests/testcase.py` | `TestCase(input, expected, rubric)` |
| `promptops/tests/dataset.py` | 2-item demo dataset |
| `promptops/api/app.py` | All FastAPI endpoints |
| `promptops/cli.py` | Typer CLI — `run`, `optimize`, `suites` |
| `promptops/core/adapter.py` | Backward-compat shim (re-exports from adapters/) |

**Frontend:**

| File | Purpose |
|---|---|
| `frontend/src/app/layout.tsx` | Root layout + sticky nav bar |
| `frontend/src/app/page.tsx` | Dashboard (server fetch → DashboardClient) |
| `frontend/src/app/components/DashboardClient.tsx` | Live KPIs, trend sparkline, auto-refresh (10s), regression badges |
| `frontend/src/app/playground/page.tsx` | A/B testing, diff view, Save Run, provider select |
| `frontend/src/app/optimize/page.tsx` | Optimizer UI → POST /optimize |
| `frontend/src/app/suites/page.tsx` | Suite CRUD — create, delete, add/remove cases |
| `frontend/src/app/runs/[id]/page.tsx` | Run detail — per-case breakdown, MLflow link |

---

## Core Concepts

### Prompt Model
```python
Prompt(
    name="my_prompt",
    system="You are a helpful assistant.",
    template="{input}",          # {placeholder} syntax, safe formatter
    model="llama3.1",
    params={"temperature": 0.2, "max_tokens": 200},
    context_limit=4096,
    output_format=None,          # "json" triggers format validation
    provider="ollama",           # "ollama" | "openai" | "anthropic"
)
```

### TestCase
```python
TestCase(
    input={"input": "Explain closures."},
    expected="A closure captures variables from its enclosing scope.",  # optional
    rubric={"factuality": 0.5, "brevity": 0.5},                        # optional
)
```

### Objective Formula
```
objective = judge_score
          - 0.2 × token_penalty        (tokens / context_limit)
          - format_penalty             (0.2 if JSON expected but invalid)
          - 0.1 × context_window_used  (same as token_penalty, double-counted intentionally)
          - 0.0001 × latency_ms
```

### Judge
- Calls the judge model 3× concurrently, averages all scores
- Returns: `{criteria: {k: score}, overall: float, reasoning: str}`
- Fallback: regex `[01](?:\.\d+)?` if JSON parse fails
- Respects `TestCase.expected` — includes in prompt if set

### Regression Detection
- After each run: `get_best_for_prompt(prompt.name)` → compare objectives
- If `new_objective < prev_best` → `regression=True`, `warnings.warn()`
- Stored as `regression INTEGER` in `runs` table
- Displayed as red "↓ Regression" badge in dashboard and run detail

---

## SQLite Schema

```sql
runs           -- one row per run (avg scores, regression flag, MLflow run_id)
run_results    -- one row per testcase per run (output, judge, criteria, metrics)
suites         -- named test collections
suite_cases    -- individual testcases belonging to a suite
```

DB path: `PROMPTOPS_DB` env var (default `./promptops.db`)

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health?provider=ollama` | Provider reachability check |
| POST | `/run` | Run prompt on demo dataset or named suite |
| POST | `/preview` | A/B compare prompts, custom inputs |
| POST | `/optimize` | Run optimization loop |
| GET | `/leaderboard` | Top 10 runs by objective |
| GET | `/runs` | Recent runs (default limit 200) |
| GET | `/runs/{id}` | Run + per-case results |
| GET/POST | `/suites` | List / create suites |
| GET/DELETE | `/suites/{id}` | Get / delete suite |
| POST | `/suites/{id}/cases` | Add case |
| DELETE | `/suites/{id}/cases/{case_id}` | Remove case |

---

## CLI

```bash
promptops run [--model llama3.1] [--judge-model llama3.1] [--provider ollama]
promptops optimize [--iterations 2] [--use-rewriter] [--provider ollama]
promptops suites list
promptops suites create "my-suite" --description "..."
promptops suites delete <id>
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_URL` | `http://localhost:11434` | Ollama server URL |
| `OPENAI_API_KEY` | — | Required for `provider=openai` |
| `ANTHROPIC_API_KEY` | — | Required for `provider=anthropic` |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowed origins |
| `PROMPTOPS_DB` | `./promptops.db` | SQLite file path |
| `MLFLOW_TRACKING_URI` | `./mlruns` | MLflow tracking directory or server URL |
| `NEXT_PUBLIC_API_URL` | `http://127.0.0.1:8000` | Backend URL (baked into frontend at build time) |
| `NEXT_PUBLIC_MLFLOW_URL` | `http://localhost:5000` | MLflow URL for run links in frontend |

---

## Running Locally

```bash
# 1. Start Ollama
ollama serve && ollama pull llama3.1

# 2. Install and start backend
pip install -e .
uvicorn promptops.api.app:app --reload --port 8000

# 3. Start frontend
cd frontend && npm install && npm run dev

# 4. Optional: MLflow UI
mlflow ui   # http://localhost:5000
```

Or with Docker:
```bash
docker compose up --build
# backend: 8000, frontend: 3000, mlflow: 5001
```

---

## Deployment (Railway)

- Backend: `railway.toml` at root — Dockerfile builder, `sh -c 'uvicorn ... --port $PORT'`
- Frontend: `frontend/railway.toml` — Nixpacks builder, `sh -c 'next start -p $PORT'`
- Push to `main` → Railway auto-deploys both services
- No Ollama on Railway — use `OPENAI_API_KEY` + `provider=openai`

---

## Adding a New Provider

1. Create `promptops/core/adapters/myprovider.py` extending `BaseAdapter`
2. Implement `generate()` and `health_check()`
3. Add a case to `make_adapter()` in `promptops/core/adapters/__init__.py`
4. Add provider name to the select dropdown in `playground/page.tsx` and `optimize/page.tsx`

---

## Important Patterns

- **Never import from `promptops.core.adapter`** — import from `promptops.core.adapters` (the package). The old `adapter.py` is a backward-compat shim only.
- **`run_prompt()` now returns a 3-tuple**: `(output, metrics, judge_info)` — not 2.
- **Judge adapter type**: `BaseAdapter`, not `OllamaAdapter` — works with any provider.
- **`insert_run()` returns the DB row ID** — use it to call `insert_run_result()`.
- **`NEXT_PUBLIC_*` vars are baked in at Next.js build time** — changing them requires a rebuild.
