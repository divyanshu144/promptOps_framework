# PromptOps

PromptOps is a **prompt‑as‑code** framework that turns prompts into versioned, testable artifacts. It runs curated test cases, scores outputs with an LLM‑judge, optimizes prompts automatically, and tracks everything with MLflow. A FastAPI backend powers an interactive Next.js + Tailwind dashboard.

## Why It Exists
Prompt engineering usually lives in notebooks and ad‑hoc scripts. PromptOps makes it **systematic and measurable**:
- define prompts in Python
- evaluate against small, high‑signal test sets
- optimize for quality + token efficiency
- track improvements and regressions over time

## Core Features
- **Prompt‑as‑code**: Python objects define system + template + params
- **Automated evals**: LLM‑judge rubric scoring
- **Optimization loop**: mutations + rewrite to improve quality and reduce tokens
- **Multi‑metric objective**: quality, tokens, latency, context usage
- **MLflow tracking**: experiment metrics + artifacts
- **API + UI**: FastAPI service + Next.js dashboard

## Primary Use Cases
- Rapid prompt iteration and benchmarking
- Model comparisons on the same prompt/test suite
- Token/cost optimization without losing quality
- Portfolio‑grade demonstration of MLOps‑style prompt workflows

---

## Project Structure
- `promptops/core/`: prompt definition, runner, model adapter
- `promptops/eval/`: judge + metrics
- `promptops/opt/`: optimizer + mutations
- `promptops/store/`: SQLite run store
- `promptops/api/`: FastAPI service
- `frontend/`: Next.js + Tailwind dashboard

---

## Quickstart (Backend)

1) Start Ollama locally.

2) Run the API:

```bash
uvicorn promptops.api.app:app --reload
```

3) Run a demo eval:

```bash
promptops run
```

4) MLflow UI:

```bash
mlflow ui --backend-store-uri ./mlruns
```

Backend dashboard:

```bash
open http://localhost:8000/dashboard
```

Optional env:
- `MLFLOW_UI_URL` to link runs from the dashboard (default `http://localhost:5000`)

---

## Frontend (Next.js + Tailwind)

```bash
cd frontend
npm install
npm run dev
```

Set API URL:

```bash
cp .env.example .env.local
```

Open:

```
http://localhost:3000
```

---

## Example Workflow

1. Define a prompt in Python.
2. Run it against a small test set.
3. Inspect scores and outputs.
4. Run the optimizer to propose variants.
5. Compare runs in MLflow + dashboard.

---

## Notes
- This project is designed for **small, curated test sets** to showcase signal‑quality evaluation.
- Ollama is the default model provider, but adapters can be extended.
