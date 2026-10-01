# Combined working-tree review

Reviewed the current working tree against HEAD on October 1, 2026. Existing uncommitted work
was preserved. This review preceded the user-authorized commit and push.

## Provenance and logical groups

| Group | Present before this task | Added or extended in this task |
|---|---|---|
| Evaluation / release gates | `eval/release.py`, tool/retrieval/grounding metrics, aggregate metrics, gate API/CLI, SQLite run/suite extensions, gate/aggregation tests | CI suite-execution command; RAG extractive and semantic harnesses; failure taxonomy; validated budgets/JSON schemas; generic gate defaults; fail-closed baseline checks; configurable threshold file |
| Optimizer reliability | Repeated evaluations, improvement heuristic, separate judge adapters, parameter-only mutation identification, optimizer/mutation tests | Reject zero repeats; isolate concurrent MLflow logging from model awaits |
| Provider / harness compatibility | DeepEval JSON/schema argument handling and metric-name fallback; local integration fixture changes | Ollama options payload correction, configured generation cost estimates for all providers, null latency handling |
| Frontend | Run metrics/trace display changes, ESLint configuration | Failure badges, gate status, aggregate metrics, readable trace JSON, dashboard gate badges, correct chronological chart/newest-first table, consistent API URL |
| Packaging / evidence | Docker port/file-store adjustments; HANDOFF, RESUME_NOTES, tasks, local Claude skills | Platform positioning, GitHub Actions gate example, JSON RAG suite/prompt pair, offline replay, live benchmark script/report, screenshots, new tests |

Several files contain both groups (`runner.py`, `metrics.py`, `cli.py`, `api/app.py`, `db.py`,
and run detail). The table is provenance, not a claim that whole-file commits can separate
changes safely. Use hunk-level staging if splitting later. Local workflow/resume notes are
optional and should be reviewed independently of product code.

## Findings addressed during this review

1. **Unfair source availability:** baseline originally received only the question. Both prompts
   now receive identical source contexts; fixture keys were updated without changing authored scores.
2. **Ollama ignored generation settings:** temperature, seed, context size, and `num_predict`
   belong in `options`. They are now nested correctly; `format`/`keep_alive` stay top-level.
   An offline request-payload test checks the output limit and deterministic settings.
3. **Overlapping fluent MLflow runs:** optimizer candidates yielded during an active fluent run,
   allowing another coroutine to close or contaminate it. Model work now completes before the
   synchronous tracking block. An actual local MLflow test evaluates two concurrent prompts and
   checks distinct parameters, metrics, and output artifacts. The environment tracking URI is honored.
4. **Misleading frontend evidence:** dashboard table/trend order was reversed, refresh ignored
   its supplied API URL, and nested provider traces rendered as `[object Object]`. These are fixed.
5. **Citation format mismatch in live generation:** an initial optimized prompt produced `[1]`
   and `['shipping']`. Exact source-ID examples were added; all three final repeats complied.
6. **Zero optimizer repeats:** rejected explicitly instead of falling through to division by zero.
7. **Frontend production type check:** failure badge formatting used `replaceAll`, which is
   outside the configured TypeScript library target. Replaced it with a compatible global regex;
   the full production build now passes.
8. **Stale local CLI installation:** refreshed the editable install; the real `promptops ci`
   command was used for both offline gates.

9. **Cloud provider integration:** added Mistral, completed OpenAI/Claude client cleanup and non-generating health checks, provider-specific CLI/UI model defaults, independent judge selection, and mocked provider tests.
10. **Local configuration:** added Mistral to `.env.example` and load local `.env` in CLI/API without overriding environment variables. The local `.env` remains Git-ignored.
11. **CI dependencies:** explicitly install `pytest-asyncio` for asynchronous offline tests.

## Evidence

- [Offline baseline CLI output](validation/baseline-offline.txt): 25%, exit 1.
- [Offline optimized CLI output](validation/optimized-offline.txt): 100%, exit 0.
- [Dashboard screenshot](screenshots/support-comparison.png).
- [Expanded unsupported-answer screenshot](screenshots/support-failure-analysis.png).
- [Measured live report](validation/live-benchmark.json): three repeats, separate local judge,
  12 answers per variant; baseline 0%, optimized 100%. Both variants receive source context.
- Final validation: **133 backend tests passed**; frontend lint passed; `npm run build` passed
  (including TypeScript checks); `git diff --check` passed.
- Remaining emitted warnings are dependency notices: MLflow file-store deprecation and
  outdated Browserslist metadata; they did not fail validation.

## Interpretation

The fixtures demonstrate the full runner/storage/API/UI flow; they do not measure prompt gains.
The live run measures citation compliance on a small development set. It does not justify a
claim of lower token use, broad hallucination reduction, or meeting latency SLOs. Actual model
latencies and token counts are preserved. Cost estimates require explicit effective rates;
no paid provider prices or hardware costs were invented.

Recommended review boundaries: evaluation/gates/storage first; optimizer/provider reliability
second; UI/evidence/packaging third. The normal test suite and GitHub Actions example are offline.
