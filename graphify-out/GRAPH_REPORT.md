# Graph Report - .  (2026-05-13)

## Corpus Check
- Corpus is ~16,717 words - fits in a single context window. You may not need a graph.

## Summary
- 346 nodes · 548 edges · 33 communities detected
- Extraction: 66% EXTRACTED · 34% INFERRED · 0% AMBIGUOUS · INFERRED: 189 edges (avg confidence: 0.77)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Core Concepts & Design Rationale|Core Concepts & Design Rationale]]
- [[_COMMUNITY_FastAPI Endpoints & Request Models|FastAPI Endpoints & Request Models]]
- [[_COMMUNITY_Provider Adapter Layer|Provider Adapter Layer]]
- [[_COMMUNITY_Frontend Data Layer & API Contracts|Frontend Data Layer & API Contracts]]
- [[_COMMUNITY_Prompt Execution Pipeline|Prompt Execution Pipeline]]
- [[_COMMUNITY_Adapter Implementations|Adapter Implementations]]
- [[_COMMUNITY_SQLite Store & DB Tests|SQLite Store & DB Tests]]
- [[_COMMUNITY_Optimize & Preview Endpoints|Optimize & Preview Endpoints]]
- [[_COMMUNITY_Prompt Mutation Engine|Prompt Mutation Engine]]
- [[_COMMUNITY_Metrics & Objective Function|Metrics & Objective Function]]
- [[_COMMUNITY_LLM Judge & Scoring|LLM Judge & Scoring]]
- [[_COMMUNITY_Judge Stability & Model Response|Judge Stability & Model Response]]
- [[_COMMUNITY_Suites Management UI|Suites Management UI]]
- [[_COMMUNITY_Optimize UI & SSE Streaming|Optimize UI & SSE Streaming]]
- [[_COMMUNITY_Playground AB Testing UI|Playground A/B Testing UI]]
- [[_COMMUNITY_Optimize Page Frontend|Optimize Page Frontend]]
- [[_COMMUNITY_Mutation & Parallel Evaluation|Mutation & Parallel Evaluation]]
- [[_COMMUNITY_Provider Health Checks|Provider Health Checks]]
- [[_COMMUNITY_Frontend Layout & Config|Frontend Layout & Config]]
- [[_COMMUNITY_CLI Suites Commands|CLI Suites Commands]]
- [[_COMMUNITY_FastAPI App Bootstrap|FastAPI App Bootstrap]]
- [[_COMMUNITY_PromptOps Package|PromptOps Package]]
- [[_COMMUNITY_CLI Suites Delete|CLI Suites Delete]]
- [[_COMMUNITY_PromptPayload Model|PromptPayload Model]]
- [[_COMMUNITY_RunRequest Model|RunRequest Model]]
- [[_COMMUNITY_PreviewRequest Model|PreviewRequest Model]]
- [[_COMMUNITY_OptimizeRequest Model|OptimizeRequest Model]]
- [[_COMMUNITY_SuiteCreateRequest Model|SuiteCreateRequest Model]]
- [[_COMMUNITY_SuiteCaseRequest Model|SuiteCaseRequest Model]]
- [[_COMMUNITY_Leaderboard Endpoint|Leaderboard Endpoint]]
- [[_COMMUNITY_Runs List Endpoint|Runs List Endpoint]]
- [[_COMMUNITY_Run Detail Endpoint|Run Detail Endpoint]]
- [[_COMMUNITY_CLAUDE.md Architecture Guide|CLAUDE.md Architecture Guide]]

## God Nodes (most connected - your core abstractions)
1. `_conn()` - 18 edges
2. `_conn` - 18 edges
3. `Prompt` - 15 edges
4. `run()` - 13 edges
5. `TestCase` - 12 edges
6. `insert_run()` - 12 edges
7. `_run()` - 12 edges
8. `make_adapter factory function` - 12 edges
9. `test_db.py — Database Unit Tests` - 11 edges
10. `run_dataset()` - 10 edges

## Surprising Connections (you probably didn't know these)
- `Prompt Versioning via SHA-256 Hash` --conceptually_related_to--> `insert_run() function`  [INFERRED]
  README.md → promptops/store/db.py
- `temp_db()` --calls--> `init_db()`  [INFERRED]
  tests/test_db.py → promptops/store/db.py
- `Regression Badge UI (red arrow indicator)` --conceptually_related_to--> `Regression Detection`  [INFERRED]
  frontend/src/app/runs/[id]/page.tsx → promptops/store/db.py
- `MLflow Run Link (NEXT_PUBLIC_MLFLOW_URL)` --conceptually_related_to--> `MLflow Artifact: outputs.txt`  [INFERRED]
  frontend/src/app/runs/[id]/page.tsx → mlruns/0/04906fd49715400f8677a096fa333d69/artifacts/outputs.txt
- `run()` --calls--> `_run()`  [INFERRED]
  promptops/cli.py → tests/test_db.py

## Hyperedges (group relationships)
- **Provider Adapter Pattern: BaseAdapter implemented by all three providers and selected via make_adapter** — base_baseadapter, ollama_ollamaadapter, openai_openaiadapter, anthropic_anthropicadapter, adapters_make_adapter [EXTRACTED 1.00]
- **Prompt Evaluation Pipeline: run_prompt/run_dataset orchestrates Prompt render, adapter generate, judge, metrics** — runner_run_prompt, runner_run_dataset, prompt_render, base_baseadapter, testcase_testcase [EXTRACTED 0.95]
- **Dual Entry Points: CLI and FastAPI API both expose run and optimize via the same core runner and optimizer** — cli_run, cli_optimize, app_run_endpoint, app_optimize_endpoint, runner_run_dataset [INFERRED 0.85]
- **Evaluation Pipeline: judge + metrics + objective** — judge_judge_output, metrics_compute_metrics, concept_objective_formula, concept_llm_judge_stability [INFERRED 0.90]
- **Optimizer Loop: mutations + rewrite + run_dataset + early stop** — optimizer_optimize_prompt, concept_early_stopping, judge_judge_output, metrics_compute_metrics [INFERRED 0.85]
- **SQLite Persistence: runs + run_results + suites + suite_cases** — db_runs_table, db_run_results_table, db_suites_table, db_suite_cases_table [EXTRACTED 1.00]
- **Prompt History Feature Flow: list → detail → run drill-down** — frontend_prompts_page, frontend_prompt_history_page, frontend_run_detail_page [EXTRACTED 0.95]
- **Judge Stability: 3x parallel calls → averaging → single score** — eval_judge_output, eval_single_judge_call, concept_3x_averaging_rationale [EXTRACTED 0.95]
- **Database Test Coverage: init_db + insert/query functions tested end-to-end** — test_db_module, store_db_module, store_suite_crud [EXTRACTED 0.95]

## Communities

### Community 0 - "Core Concepts & Design Rationale"
Cohesion: 0.06
Nodes (43): Dashboard Auto-Refresh (10s), Optimization Loop — mutations + LLM rewrite + parallel eval + early stop, Prompt Versioning via SHA-256 Hash, Regression Detection, add_suite_case, _conn, create_suite, DB_PATH (+35 more)

### Community 1 - "FastAPI Endpoints & Request Models"
Cohesion: 0.11
Nodes (32): add_suite_case_endpoint(), create_suite_endpoint(), delete_suite_endpoint(), get_suite_endpoint(), leaderboard(), lifespan(), list_suites_endpoint(), prompt_history() (+24 more)

### Community 2 - "Provider Adapter Layer"
Cohesion: 0.11
Nodes (31): adapter.py backward-compat shim, make_adapter factory function, AnthropicAdapter class, AnthropicAdapter.generate method, GET /health endpoint, POST /optimize endpoint, POST /optimize/stream SSE endpoint, POST /preview endpoint (+23 more)

### Community 3 - "Frontend Data Layer & API Contracts"
Cohesion: 0.08
Nodes (26): GET /prompts/{name}/history API Endpoint, GET /prompts API Endpoint, GET /runs/{id} API Endpoint, SQLite over Postgres Design Rationale, MLflow Run Link (NEXT_PUBLIC_MLFLOW_URL), Prompt History Detail Page, PromptSummary Type (prompt_name, run_count, best_objective, avg_objective, last_run_at), Prompts List Page (+18 more)

### Community 4 - "Prompt Execution Pipeline"
Cohesion: 0.17
Nodes (19): generate(), run(), prompt_hash(), run_dataset(), run_prompt(), run_prompt_detailed(), judge_output(), JudgeResult (+11 more)

### Community 5 - "Adapter Implementations"
Cohesion: 0.15
Nodes (10): ABC, AnthropicAdapter, BaseAdapter, health_check(), ModelResponse, make_adapter(), OllamaAdapter, OpenAIAdapter (+2 more)

### Community 6 - "SQLite Store & DB Tests"
Cohesion: 0.27
Nodes (16): get_best_for_prompt(), get_run(), insert_run(), _run(), temp_db(), test_get_best_for_prompt_picks_highest_objective(), test_get_best_for_prompt_returns_none_when_missing(), test_get_prompt_history_ordered_asc() (+8 more)

### Community 7 - "Optimize & Preview Endpoints"
Cohesion: 0.24
Nodes (14): optimize(), OptimizeRequest, preview(), PreviewRequest, PromptPayload, RunRequest, SuiteCaseRequest, SuiteCreateRequest (+6 more)

### Community 8 - "Prompt Mutation Engine"
Cohesion: 0.39
Nodes (10): basic_mutations(), _prompt(), test_all_variant_names_present(), test_count_with_max_tokens(), test_count_without_max_tokens(), test_fewshot_fallback_without_testcases(), test_fewshot_injects_testcase_examples(), test_json_variants_set_output_format() (+2 more)

### Community 9 - "Metrics & Objective Function"
Cohesion: 0.33
Nodes (8): compute_metrics(), RunMetrics, test_basic_objective_is_penalized(), test_format_penalty_applied_when_invalid(), test_latency_penalty(), test_no_format_penalty_when_valid(), test_none_tokens_zero_penalty(), test_token_penalty_proportional_to_context()

### Community 10 - "LLM Judge & Scoring"
Cohesion: 0.2
Nodes (10): Early Stop (min_delta), LLM Judge 3x Stability Averaging, Objective Formula, judge_output, JUDGE_PROMPT, JudgeResult, _single_judge_call, compute_metrics (+2 more)

### Community 11 - "Judge Stability & Model Response"
Cohesion: 0.22
Nodes (9): ModelResponse Pydantic model, 3x Judge Calls Averaging Rationale, LLM-as-Judge Design Rationale, Multi-Metric Objective Design Rationale, compute_metrics() function, judge_output() function, _single_judge_call() function, test_judge.py — Judge Unit Tests (+1 more)

### Community 12 - "Suites Management UI"
Cohesion: 0.46
Nodes (6): addCase(), createSuite(), deleteSuite(), loadSuite(), loadSuites(), removeCase()

### Community 13 - "Optimize UI & SSE Streaming"
Cohesion: 0.25
Nodes (8): SSE Streaming Progress (optimize), Word-level Diff (A/B), OptimizePage, runOptimize, diffTokens, Playground, runPreview, saveRun

### Community 14 - "Playground A/B Testing UI"
Cohesion: 0.47
Nodes (3): apiError(), runPreview(), saveRun()

### Community 15 - "Optimize Page Frontend"
Cohesion: 0.6
Nodes (3): apiError(), runOptimize(), scrollProgress()

### Community 16 - "Mutation & Parallel Evaluation"
Cohesion: 0.4
Nodes (5): Parallel Candidate Evaluation Rationale, Prompt Pydantic Model, basic_mutations() function, test_mutations.py — Mutation Unit Tests, TestCase dataclass

### Community 19 - "Provider Health Checks"
Cohesion: 0.67
Nodes (3): AnthropicAdapter.health_check method, OllamaAdapter.health_check method, OpenAIAdapter.health_check method

### Community 20 - "Frontend Layout & Config"
Cohesion: 0.67
Nodes (3): RootLayout, NavBar, Next.js Config

### Community 26 - "CLI Suites Commands"
Cohesion: 1.0
Nodes (2): CLI suites create command, CLI suites list command

### Community 27 - "FastAPI App Bootstrap"
Cohesion: 1.0
Nodes (2): FastAPI app instance, FastAPI lifespan context manager

### Community 41 - "PromptOps Package"
Cohesion: 1.0
Nodes (1): promptops Package

### Community 42 - "CLI Suites Delete"
Cohesion: 1.0
Nodes (1): CLI suites delete command

### Community 43 - "PromptPayload Model"
Cohesion: 1.0
Nodes (1): PromptPayload request model

### Community 44 - "RunRequest Model"
Cohesion: 1.0
Nodes (1): RunRequest model

### Community 45 - "PreviewRequest Model"
Cohesion: 1.0
Nodes (1): PreviewRequest model

### Community 46 - "OptimizeRequest Model"
Cohesion: 1.0
Nodes (1): OptimizeRequest model

### Community 47 - "SuiteCreateRequest Model"
Cohesion: 1.0
Nodes (1): SuiteCreateRequest model

### Community 48 - "SuiteCaseRequest Model"
Cohesion: 1.0
Nodes (1): SuiteCaseRequest model

### Community 49 - "Leaderboard Endpoint"
Cohesion: 1.0
Nodes (1): GET /leaderboard endpoint

### Community 50 - "Runs List Endpoint"
Cohesion: 1.0
Nodes (1): GET /runs endpoint

### Community 51 - "Run Detail Endpoint"
Cohesion: 1.0
Nodes (1): GET /runs/{run_id} endpoint

### Community 52 - "CLAUDE.md Architecture Guide"
Cohesion: 1.0
Nodes (1): CLAUDE.md — Project Architecture Guide

## Knowledge Gaps
- **66 isolated node(s):** `promptops Package`, `CLI suites list command`, `CLI suites create command`, `CLI suites delete command`, `_SafeFormatter inner class` (+61 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `CLI Suites Commands`** (2 nodes): `CLI suites create command`, `CLI suites list command`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `FastAPI App Bootstrap`** (2 nodes): `FastAPI app instance`, `FastAPI lifespan context manager`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `PromptOps Package`** (1 nodes): `promptops Package`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `CLI Suites Delete`** (1 nodes): `CLI suites delete command`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `PromptPayload Model`** (1 nodes): `PromptPayload request model`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `RunRequest Model`** (1 nodes): `RunRequest model`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `PreviewRequest Model`** (1 nodes): `PreviewRequest model`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `OptimizeRequest Model`** (1 nodes): `OptimizeRequest model`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `SuiteCreateRequest Model`** (1 nodes): `SuiteCreateRequest model`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `SuiteCaseRequest Model`** (1 nodes): `SuiteCaseRequest model`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Leaderboard Endpoint`** (1 nodes): `GET /leaderboard endpoint`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Runs List Endpoint`** (1 nodes): `GET /runs endpoint`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Run Detail Endpoint`** (1 nodes): `GET /runs/{run_id} endpoint`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `CLAUDE.md Architecture Guide`** (1 nodes): `CLAUDE.md — Project Architecture Guide`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `run_dataset()` connect `Prompt Execution Pipeline` to `FastAPI Endpoints & Request Models`, `Adapter Implementations`, `SQLite Store & DB Tests`?**
  _High betweenness centrality (0.037) - this node is a cross-community bridge._
- **Why does `run()` connect `Prompt Execution Pipeline` to `FastAPI Endpoints & Request Models`, `Adapter Implementations`, `Optimize & Preview Endpoints`?**
  _High betweenness centrality (0.036) - this node is a cross-community bridge._
- **Why does `Regression Detection` connect `Core Concepts & Design Rationale` to `LLM Judge & Scoring`, `Frontend Data Layer & API Contracts`?**
  _High betweenness centrality (0.031) - this node is a cross-community bridge._
- **Are the 12 inferred relationships involving `Prompt` (e.g. with `PromptPayload` and `RunRequest`) actually correct?**
  _`Prompt` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `run()` (e.g. with `make_adapter()` and `Prompt`) actually correct?**
  _`run()` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `TestCase` (e.g. with `PromptPayload` and `RunRequest`) actually correct?**
  _`TestCase` has 11 INFERRED edges - model-reasoned connections that need verification._
- **What connects `promptops Package`, `CLI suites list command`, `CLI suites create command` to the rest of the system?**
  _66 weakly-connected nodes found - possible documentation gaps or missing edges._