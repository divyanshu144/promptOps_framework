# Eval Harness Design

**Date:** 2026-05-25
**Status:** Approved

## Problem

PromptOps uses a custom LLM-as-judge loop that works well but has no connection to established eval frameworks (DeepEval, RAGAS, Braintrust). The current design makes it hard to swap in different eval strategies or run evals as part of CI. This makes it difficult to demonstrate "eval as an ongoing discipline."

## Goal

Add an `EvalHarness` abstraction layer that makes the eval strategy pluggable, wire in DeepEval as the first concrete implementation (routing through the existing adapter so no new API keys are needed), and add a pytest-based eval test suite that can run in CI.

---

## Architecture

### New files

| File | Purpose |
|---|---|
| `promptops/eval/harness.py` | `EvalHarness` ABC — the swappable eval interface |
| `promptops/eval/llm_judge_harness.py` | `LLMJudgeHarness` — wraps existing `judge_output()` unchanged |
| `promptops/eval/deepeval_harness.py` | `DeepEvalHarness` + `PromptOpsDeepEvalLLM` bridge |
| `promptops/tests/evals/conftest.py` | pytest fixtures: adapter, prompt, dataset |
| `promptops/tests/evals/test_prompt_quality.py` | pytest eval tests using DeepEval `assert_test` |

### Modified files

| File | Change |
|---|---|
| `promptops/core/runner.py` | `run_dataset()` and `run_prompt()` accept `harness: EvalHarness | None = None` |
| `promptops/api/app.py` | `/run` endpoint accepts optional `"eval_harness": "deepeval"` in request body |
| `setup.py` | Add `deepeval` as a required dependency |

---

## Component Design

### `EvalHarness` ABC (`promptops/eval/harness.py`)

```python
class EvalHarness(ABC):
    @abstractmethod
    async def evaluate(
        self,
        user_input: Dict[str, Any],
        actual_output: str,
        expected_output: str | None,
        rubric: Dict[str, Any] | None,
    ) -> JudgeResult:
        ...
```

`JudgeResult` is reused from `judge.py` unchanged (`score`, `criteria`, `reasoning`). Nothing downstream — metrics computation, SQLite storage, dashboard — needs to change.

### `LLMJudgeHarness` (`promptops/eval/llm_judge_harness.py`)

Thin wrapper around the existing `judge_output()`. It is the default when `harness=None` is passed to `run_dataset()` — preserving all current behavior exactly.

```python
class LLMJudgeHarness(EvalHarness):
    def __init__(self, adapter: BaseAdapter, model: str): ...
    async def evaluate(self, ...) -> JudgeResult:
        return await judge_output(self.adapter, self.model, rubric, user_input, actual_output, expected)
```

### `DeepEvalHarness` (`promptops/eval/deepeval_harness.py`)

Two parts:

**`PromptOpsDeepEvalLLM`** — implements DeepEval's `DeepEvalBaseLLM` interface and routes all metric calls through the existing `BaseAdapter`. This means DeepEval works with Ollama, OpenAI, or Anthropic — whichever is already configured. No separate API key required.

```python
class PromptOpsDeepEvalLLM(DeepEvalBaseLLM):
    def __init__(self, adapter: BaseAdapter, model: str): ...
    def generate(self, prompt: str) -> str: ...         # sync wrapper via thread executor (avoids blocking running event loop)
    async def a_generate(self, prompt: str) -> str: ... # native async path — used by a_measure()
    def get_model_name(self) -> str: return self.model
```

**`DeepEvalHarness`** — constructs DeepEval metrics with the bridge LLM and runs them concurrently:

```python
class DeepEvalHarness(EvalHarness):
    def __init__(self, adapter: BaseAdapter, model: str):
        llm = PromptOpsDeepEvalLLM(adapter, model)
        self._llm = llm
        # metrics are built per-call in evaluate() so evaluation_params can
        # conditionally include EXPECTED_OUTPUT only when expected is provided

    async def evaluate(self, user_input, actual_output, expected_output, rubric) -> JudgeResult:
        eval_params = [LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT]
        if expected_output is not None:
            eval_params.append(LLMTestCaseParams.EXPECTED_OUTPUT)
        metrics = [
            GEval(name="Quality",
                  criteria="Is the output factually correct, coherent, and directly addresses the input?",
                  evaluation_params=eval_params, model=self._llm, threshold=0.5),
            AnswerRelevancyMetric(model=self._llm, threshold=0.5),
        ]
        test_case = LLMTestCase(
            input=json.dumps(user_input),
            actual_output=actual_output,
            expected_output=expected_output,
        )
        await asyncio.gather(*[m.a_measure(test_case) for m in metrics])
        # aggregate metric scores into JudgeResult
        scores = {m.name: m.score for m in metrics}
        avg = sum(scores.values()) / len(scores)
        reasoning = "; ".join(
            f"{m.name}: {getattr(m, 'reason', '')}" for m in metrics
        )
        criteria = {k: float(v) for k, v in scores.items()}
        return JudgeResult(score=avg, criteria=criteria, reasoning=reasoning)
```

### `runner.py` changes

`run_dataset()` and `run_prompt()` each gain one new optional parameter:

```python
async def run_dataset(
    ...,
    harness: EvalHarness | None = None,
) -> dict[str, Any]:
    if harness is None:
        harness = LLMJudgeHarness(adapter, judge_model)
    # replace judge_output() calls with harness.evaluate()
```

### API changes (`app.py`)

`POST /run` request body gains an optional field:

```json
{ "eval_harness": "deepeval" }
```

When `"deepeval"` is specified, the endpoint constructs `DeepEvalHarness(adapter, judge_model)` before calling `run_dataset()`. Omitting the field preserves existing behavior.

---

## Pytest Integration

```
promptops/tests/evals/
├── conftest.py
└── test_prompt_quality.py
```

### `conftest.py`

Provides session-scoped fixtures:
- `adapter` — `OllamaAdapter` from env (calls `health_check()`; skips all eval tests if unreachable)
- `default_prompt` — a minimal `Prompt` object pointing at `llama3.1`
- `deepeval_llm` — a `PromptOpsDeepEvalLLM(adapter, "llama3.1")` instance for use in test metrics
- `generate_output(adapter, prompt, text) -> str` — async helper that renders a prompt and returns the raw output string

### `test_prompt_quality.py`

```python
@pytest.mark.asyncio
@pytest.mark.deepeval
async def test_closure_explanation(adapter, default_prompt, deepeval_llm):
    output = await generate_output(adapter, default_prompt, "Explain closures in Python")
    test_case = LLMTestCase(
        input="Explain closures in Python",
        actual_output=output,
    )
    assert_test(test_case, [
        GEval(
            name="Factuality",
            criteria="Is the output factually correct about Python closures?",
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            model=deepeval_llm,
            threshold=0.6,
        ),
        AnswerRelevancyMetric(model=deepeval_llm, threshold=0.5),
    ])
```

Run with: `pytest -m deepeval promptops/tests/evals/`

DeepEval's pytest plugin captures metric scores per test and surfaces pass/fail per criterion in the test report. In CI, this is the concrete evidence of "evals running as an ongoing discipline."

---

## Dependency

Add to `setup.py` `install_requires`:

```
deepeval>=0.21
```

No optional extras — `deepeval` is a first-class dependency.

---

## What Stays Unchanged

- `judge.py`, `metrics.py`, `testcase.py`, `dataset.py` — untouched
- All existing API endpoints and CLI commands — same behavior when `eval_harness` is omitted
- SQLite schema, MLflow logging, regression detection — no changes
- Dashboard, playground, optimizer UI — no changes

---

## Out of Scope

- RAGAS or Braintrust adapters (can be added as future `EvalHarness` implementations)
- Dataset versioning / golden dataset management
- DeepEval dashboard / Confident AI integration
