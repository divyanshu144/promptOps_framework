# Eval Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a pluggable `EvalHarness` abstraction to PromptOps, wire DeepEval in as the first concrete implementation, and add a pytest-based eval suite that runs in CI.

**Architecture:** Define an `EvalHarness` ABC that both the existing LLM judge and DeepEval implement. `runner.py` and the `/run` endpoint accept an optional `harness=` param; the default is `LLMJudgeHarness` so all existing behaviour is preserved. A `PromptOpsDeepEvalLLM` bridge routes DeepEval's metric calls through the existing `BaseAdapter`, so no new API keys are needed.

**Tech Stack:** Python 3.11+, deepeval>=0.21, FastAPI, pytest, asyncio, unittest.mock

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Create | `promptops/eval/harness.py` | `EvalHarness` ABC |
| Create | `promptops/eval/llm_judge_harness.py` | Wraps existing `judge_output()` |
| Create | `promptops/eval/deepeval_harness.py` | `PromptOpsDeepEvalLLM` bridge + `DeepEvalHarness` |
| Create | `tests/test_harness.py` | Unit tests for ABC + `LLMJudgeHarness` |
| Create | `tests/test_deepeval_harness.py` | Unit tests for bridge + `DeepEvalHarness` |
| Create | `tests/test_runner_harness.py` | Unit tests for runner.py harness param |
| Create | `promptops/tests/evals/__init__.py` | Package marker |
| Create | `promptops/tests/evals/conftest.py` | Session fixtures for integration eval tests |
| Create | `promptops/tests/evals/test_prompt_quality.py` | DeepEval pytest integration eval tests |
| Modify | `pyproject.toml` | Add `deepeval>=0.21` to dependencies |
| Modify | `promptops/core/runner.py` | Add `harness` param to `run_prompt` + `run_dataset` |
| Modify | `promptops/api/app.py` | Add `eval_harness` field to `RunRequest` + construct harness in endpoint |

---

## Task 1: Add deepeval dependency

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add deepeval to pyproject.toml**

In `pyproject.toml`, add `"deepeval>=0.21"` to the `dependencies` list:

```toml
dependencies = [
  "fastapi>=0.110",
  "uvicorn>=0.27",
  "pydantic>=2.6",
  "httpx>=0.27",
  "typer>=0.12",
  "mlflow>=2.10",
  "python-dotenv>=1.0",
  "openai>=1.30",
  "anthropic>=0.28",
  "deepeval>=0.21",
]
```

- [ ] **Step 2: Install and verify**

```bash
pip install -e .
python -c "import deepeval; print('deepeval OK')"
```

Expected: `deepeval OK`

---

## Task 2: EvalHarness ABC

**Files:**
- Create: `promptops/eval/harness.py`
- Create: `tests/test_harness.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_harness.py`:

```python
import pytest
from promptops.eval.harness import EvalHarness


def test_eval_harness_is_abstract():
    with pytest.raises(TypeError):
        EvalHarness()


def test_eval_harness_has_evaluate_method():
    assert hasattr(EvalHarness, "evaluate")
```

- [ ] **Step 2: Run to confirm it fails**

```bash
pytest tests/test_harness.py -v
```

Expected: `ImportError` or `ModuleNotFoundError` — `harness.py` doesn't exist yet.

- [ ] **Step 3: Implement `EvalHarness`**

Create `promptops/eval/harness.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

from promptops.eval.judge import JudgeResult


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

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_harness.py -v
```

Expected: 2 passed.

---

## Task 3: LLMJudgeHarness

**Files:**
- Create: `promptops/eval/llm_judge_harness.py`
- Modify: `tests/test_harness.py`

- [ ] **Step 1: Add failing tests to `tests/test_harness.py`**

Append to `tests/test_harness.py`:

```python
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from promptops.eval.llm_judge_harness import LLMJudgeHarness
from promptops.eval.judge import JudgeResult
from promptops.core.adapters.base import ModelResponse


def _mock_adapter(output: str) -> MagicMock:
    adapter = MagicMock()
    resp = ModelResponse(output=output, prompt_tokens=5, completion_tokens=10)
    adapter.generate = AsyncMock(return_value=resp)
    return adapter


def test_llm_judge_harness_delegates_to_judge_output():
    adapter = _mock_adapter("")
    harness = LLMJudgeHarness(adapter=adapter, model="llama3.1")
    expected = JudgeResult(score=0.8, criteria={"quality": 0.8}, reasoning="good")

    with patch("promptops.eval.llm_judge_harness.judge_output", return_value=expected) as mock_judge:
        result = asyncio.run(
            harness.evaluate(
                user_input={"input": "test"},
                actual_output="test output",
                expected_output=None,
                rubric={"quality": 1.0},
            )
        )

    mock_judge.assert_called_once_with(
        adapter=adapter,
        model="llama3.1",
        rubric={"quality": 1.0},
        user_input={"input": "test"},
        assistant_output="test output",
        expected=None,
    )
    assert result.score == 0.8


def test_llm_judge_harness_uses_default_rubric_when_none():
    adapter = _mock_adapter("")
    harness = LLMJudgeHarness(adapter=adapter, model="llama3.1")
    expected = JudgeResult(score=0.5, criteria={}, reasoning=None)

    with patch("promptops.eval.llm_judge_harness.judge_output", return_value=expected) as mock_judge:
        asyncio.run(
            harness.evaluate(
                user_input={"input": "x"},
                actual_output="y",
                expected_output=None,
                rubric=None,
            )
        )

    call_kwargs = mock_judge.call_args.kwargs
    assert call_kwargs["rubric"] == {"quality": 1.0}
```

- [ ] **Step 2: Run to confirm they fail**

```bash
pytest tests/test_harness.py -v
```

Expected: `ImportError` — `llm_judge_harness.py` doesn't exist yet.

- [ ] **Step 3: Implement `LLMJudgeHarness`**

Create `promptops/eval/llm_judge_harness.py`:

```python
from __future__ import annotations

from typing import Any, Dict

from promptops.core.adapters.base import BaseAdapter
from promptops.eval.harness import EvalHarness
from promptops.eval.judge import JudgeResult, judge_output


class LLMJudgeHarness(EvalHarness):
    def __init__(self, adapter: BaseAdapter, model: str) -> None:
        self._adapter = adapter
        self._model = model

    async def evaluate(
        self,
        user_input: Dict[str, Any],
        actual_output: str,
        expected_output: str | None,
        rubric: Dict[str, Any] | None,
    ) -> JudgeResult:
        return await judge_output(
            adapter=self._adapter,
            model=self._model,
            rubric=rubric or {"quality": 1.0},
            user_input=user_input,
            assistant_output=actual_output,
            expected=expected_output,
        )
```

- [ ] **Step 4: Run all harness tests**

```bash
pytest tests/test_harness.py -v
```

Expected: 4 passed.

---

## Task 4: PromptOpsDeepEvalLLM bridge

**Files:**
- Create: `promptops/eval/deepeval_harness.py`
- Create: `tests/test_deepeval_harness.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_deepeval_harness.py`:

```python
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from promptops.core.adapters.base import ModelResponse
from promptops.eval.deepeval_harness import PromptOpsDeepEvalLLM


def _mock_adapter(output: str) -> MagicMock:
    adapter = MagicMock()
    resp = ModelResponse(output=output, prompt_tokens=5, completion_tokens=10)
    adapter.generate = AsyncMock(return_value=resp)
    return adapter


def test_a_generate_routes_through_adapter():
    adapter = _mock_adapter("bridge response")
    bridge = PromptOpsDeepEvalLLM(adapter=adapter, model="llama3.1")

    result = asyncio.run(bridge.a_generate("hello"))

    adapter.generate.assert_called_once_with(
        model="llama3.1",
        system="",
        prompt="hello",
        params={"temperature": 0.0, "max_tokens": 1000},
    )
    assert result == "bridge response"


def test_generate_sync_wrapper_returns_output():
    adapter = _mock_adapter("sync response")
    bridge = PromptOpsDeepEvalLLM(adapter=adapter, model="llama3.1")

    result = bridge.generate("sync prompt")

    assert result == "sync response"


def test_get_model_name():
    adapter = MagicMock()
    bridge = PromptOpsDeepEvalLLM(adapter=adapter, model="llama3.1")
    assert bridge.get_model_name() == "llama3.1"
```

- [ ] **Step 2: Run to confirm they fail**

```bash
pytest tests/test_deepeval_harness.py -v
```

Expected: `ImportError` — `deepeval_harness.py` doesn't exist yet.

- [ ] **Step 3: Implement `PromptOpsDeepEvalLLM`**

Create `promptops/eval/deepeval_harness.py` with just the bridge for now:

```python
from __future__ import annotations

import asyncio
import json
from typing import Any, Dict

from deepeval.models.base_model import DeepEvalBaseLLM
from deepeval.metrics import GEval, AnswerRelevancyMetric
from deepeval.test_case import LLMTestCase, LLMTestCaseParams

from promptops.core.adapters.base import BaseAdapter
from promptops.eval.harness import EvalHarness
from promptops.eval.judge import JudgeResult


class PromptOpsDeepEvalLLM(DeepEvalBaseLLM):
    def __init__(self, adapter: BaseAdapter, model: str) -> None:
        self._adapter = adapter
        self._model = model

    def get_model_name(self) -> str:
        return self._model

    async def a_generate(self, prompt: str) -> str:
        resp = await self._adapter.generate(
            model=self._model,
            system="",
            prompt=prompt,
            params={"temperature": 0.0, "max_tokens": 1000},
        )
        return resp.output

    def generate(self, prompt: str) -> str:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self.a_generate(prompt))
        finally:
            loop.close()
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_deepeval_harness.py -v
```

Expected: 3 passed.

---

## Task 5: DeepEvalHarness

**Files:**
- Modify: `promptops/eval/deepeval_harness.py`
- Modify: `tests/test_deepeval_harness.py`

- [ ] **Step 1: Add failing tests to `tests/test_deepeval_harness.py`**

Append to `tests/test_deepeval_harness.py`:

```python
from unittest.mock import patch
from promptops.eval.deepeval_harness import DeepEvalHarness
from promptops.eval.judge import JudgeResult


def _make_mock_metric(name: str, score: float, reason: str) -> MagicMock:
    m = MagicMock()
    m.name = name
    m.score = score
    m.reason = reason
    m.a_measure = AsyncMock()
    return m


def test_deepeval_harness_returns_judge_result():
    adapter = _mock_adapter("")

    with patch("promptops.eval.deepeval_harness.GEval") as MockGEval, \
         patch("promptops.eval.deepeval_harness.AnswerRelevancyMetric") as MockAR:

        mock_geval = _make_mock_metric("Quality", 0.8, "factually correct")
        mock_ar = _make_mock_metric("AnswerRelevancy", 0.6, "relevant")
        MockGEval.return_value = mock_geval
        MockAR.return_value = mock_ar

        harness = DeepEvalHarness(adapter=adapter, model="llama3.1")
        result = asyncio.run(
            harness.evaluate(
                user_input={"input": "test"},
                actual_output="test output",
                expected_output=None,
                rubric=None,
            )
        )

    assert isinstance(result, JudgeResult)
    assert result.score == pytest.approx(0.7)   # (0.8 + 0.6) / 2
    assert result.criteria["Quality"] == pytest.approx(0.8)
    assert result.criteria["AnswerRelevancy"] == pytest.approx(0.6)
    assert "Quality" in result.reasoning
    assert "AnswerRelevancy" in result.reasoning


def test_deepeval_harness_excludes_expected_output_param_when_none():
    adapter = _mock_adapter("")

    with patch("promptops.eval.deepeval_harness.GEval") as MockGEval, \
         patch("promptops.eval.deepeval_harness.AnswerRelevancyMetric") as MockAR:

        mock_geval = _make_mock_metric("Quality", 0.7, "ok")
        mock_ar = _make_mock_metric("AnswerRelevancy", 0.7, "ok")
        MockGEval.return_value = mock_geval
        MockAR.return_value = mock_ar

        harness = DeepEvalHarness(adapter=adapter, model="llama3.1")
        asyncio.run(
            harness.evaluate(
                user_input={"input": "x"},
                actual_output="y",
                expected_output=None,
                rubric=None,
            )
        )

    call_kwargs = MockGEval.call_args.kwargs
    assert LLMTestCaseParams.EXPECTED_OUTPUT not in call_kwargs["evaluation_params"]


def test_deepeval_harness_includes_expected_output_param_when_provided():
    adapter = _mock_adapter("")

    with patch("promptops.eval.deepeval_harness.GEval") as MockGEval, \
         patch("promptops.eval.deepeval_harness.AnswerRelevancyMetric") as MockAR:

        mock_geval = _make_mock_metric("Quality", 0.9, "ok")
        mock_ar = _make_mock_metric("AnswerRelevancy", 0.9, "ok")
        MockGEval.return_value = mock_geval
        MockAR.return_value = mock_ar

        harness = DeepEvalHarness(adapter=adapter, model="llama3.1")
        asyncio.run(
            harness.evaluate(
                user_input={"input": "x"},
                actual_output="y",
                expected_output="expected answer",
                rubric=None,
            )
        )

    call_kwargs = MockGEval.call_args.kwargs
    assert LLMTestCaseParams.EXPECTED_OUTPUT in call_kwargs["evaluation_params"]
```

- [ ] **Step 2: Run to confirm they fail**

```bash
pytest tests/test_deepeval_harness.py -v
```

Expected: last 3 tests fail with `ImportError` — `DeepEvalHarness` not defined yet.

- [ ] **Step 3: Implement `DeepEvalHarness`**

Append to `promptops/eval/deepeval_harness.py` (after the `PromptOpsDeepEvalLLM` class):

```python
class DeepEvalHarness(EvalHarness):
    def __init__(self, adapter: BaseAdapter, model: str) -> None:
        self._llm = PromptOpsDeepEvalLLM(adapter, model)

    async def evaluate(
        self,
        user_input: Dict[str, Any],
        actual_output: str,
        expected_output: str | None,
        rubric: Dict[str, Any] | None,
    ) -> JudgeResult:
        eval_params = [LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT]
        if expected_output is not None:
            eval_params.append(LLMTestCaseParams.EXPECTED_OUTPUT)

        metrics = [
            GEval(
                name="Quality",
                criteria="Is the output factually correct, coherent, and directly addresses the input?",
                evaluation_params=eval_params,
                model=self._llm,
                threshold=0.5,
            ),
            AnswerRelevancyMetric(model=self._llm, threshold=0.5),
        ]

        test_case = LLMTestCase(
            input=json.dumps(user_input),
            actual_output=actual_output,
            expected_output=expected_output,
        )
        await asyncio.gather(*[m.a_measure(test_case) for m in metrics])

        scores = {m.name: float(m.score) for m in metrics}
        avg = sum(scores.values()) / len(scores)
        reasoning = "; ".join(
            f"{m.name}: {getattr(m, 'reason', '')}" for m in metrics
        )
        return JudgeResult(score=avg, criteria=scores, reasoning=reasoning)
```

- [ ] **Step 4: Run all deepeval harness tests**

```bash
pytest tests/test_deepeval_harness.py -v
```

Expected: 6 passed.

---

## Task 6: runner.py — harness param

**Files:**
- Modify: `promptops/core/runner.py`
- Create: `tests/test_runner_harness.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_runner_harness.py`:

```python
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from promptops.core.adapters.base import ModelResponse
from promptops.core.prompt import Prompt
from promptops.core.runner import run_prompt, run_dataset
from promptops.eval.judge import JudgeResult
from promptops.tests.testcase import TestCase


def _mock_adapter(output: str = "response") -> MagicMock:
    adapter = MagicMock()
    resp = ModelResponse(output=output, prompt_tokens=10, completion_tokens=20)
    adapter.generate = AsyncMock(return_value=resp)
    adapter.health_check = AsyncMock(return_value=True)
    return adapter


def _default_prompt() -> Prompt:
    return Prompt(
        name="test",
        system="You are helpful.",
        template="{input}",
        model="llama3.1",
        params={"temperature": 0.2, "max_tokens": 200},
        context_limit=4096,
        provider="ollama",
    )


def _default_testcase() -> TestCase:
    return TestCase(input={"input": "hello"}, expected=None, rubric={"quality": 1.0})


def test_run_prompt_uses_provided_harness():
    adapter = _mock_adapter()
    prompt = _default_prompt()
    tc = _default_testcase()

    mock_harness = MagicMock()
    mock_harness.evaluate = AsyncMock(
        return_value=JudgeResult(score=0.9, criteria={"quality": 0.9}, reasoning="great")
    )

    output, metrics, judge_info = asyncio.run(
        run_prompt(adapter, prompt, tc, judge_model="llama3.1", harness=mock_harness)
    )

    mock_harness.evaluate.assert_called_once_with(
        user_input={"input": "hello"},
        actual_output="response",
        expected_output=None,
        rubric={"quality": 1.0},
    )
    assert judge_info["judge_score"] == pytest.approx(0.9)


def test_run_prompt_defaults_to_llm_judge_harness_when_none():
    adapter = _mock_adapter()
    prompt = _default_prompt()
    tc = _default_testcase()

    judge_result = JudgeResult(score=0.7, criteria={}, reasoning="ok")

    with patch("promptops.core.runner.LLMJudgeHarness") as MockHarness:
        mock_instance = MagicMock()
        mock_instance.evaluate = AsyncMock(return_value=judge_result)
        MockHarness.return_value = mock_instance

        asyncio.run(run_prompt(adapter, prompt, tc, judge_model="llama3.1", harness=None))

    MockHarness.assert_called_once_with(adapter, "llama3.1")


def test_run_dataset_passes_harness_to_run_prompt():
    adapter = _mock_adapter()
    prompt = _default_prompt()
    tcs = [_default_testcase()]

    mock_harness = MagicMock()
    mock_harness.evaluate = AsyncMock(
        return_value=JudgeResult(score=0.8, criteria={}, reasoning="good")
    )

    mock_run_info = MagicMock()
    mock_run_info.info.run_id = "test-run-id"
    mock_ctx = MagicMock()
    mock_ctx.__enter__ = MagicMock(return_value=mock_run_info)
    mock_ctx.__exit__ = MagicMock(return_value=False)

    with patch("promptops.core.runner.init_db"), \
         patch("promptops.core.runner.mlflow") as mock_mlflow, \
         patch("promptops.core.runner.insert_run", return_value=1), \
         patch("promptops.core.runner.insert_run_result"), \
         patch("promptops.core.runner.get_best_for_prompt", return_value=None):
        mock_mlflow.active_run.return_value = None
        mock_mlflow.start_run.return_value = mock_ctx
        result = asyncio.run(
            run_dataset(adapter, prompt, tcs, judge_model="llama3.1", harness=mock_harness)
        )

    mock_harness.evaluate.assert_called_once()
    assert result["avg_judge_score"] == pytest.approx(0.8)
```

- [ ] **Step 2: Run to confirm they fail**

```bash
pytest tests/test_runner_harness.py -v
```

Expected: all 3 fail — `run_prompt` and `run_dataset` don't accept `harness` yet.

- [ ] **Step 3: Modify `promptops/core/runner.py`**

Add the two new imports after the existing imports block (after line 22):

```python
from promptops.eval.harness import EvalHarness
from promptops.eval.llm_judge_harness import LLMJudgeHarness
```

Replace the entire `run_prompt` function (lines 30–81) with:

```python
async def run_prompt(
    adapter: BaseAdapter,
    prompt: Prompt,
    testcase: TestCase,
    judge_model: str,
    harness: EvalHarness | None = None,
) -> tuple[str, RunMetrics, dict[str, Any]]:
    if harness is None:
        harness = LLMJudgeHarness(adapter, judge_model)

    rendered = prompt.render(**testcase.input)

    start = time.time()
    resp = await adapter.generate(
        model=prompt.model,
        system=prompt.system,
        prompt=rendered,
        params=prompt.params,
    )
    latency_ms = (time.time() - start) * 1000.0

    judge = await harness.evaluate(
        user_input=testcase.input,
        actual_output=resp.output,
        expected_output=testcase.expected,
        rubric=testcase.rubric,
    )

    format_valid = None
    if prompt.output_format == "json" or prompt.output_schema is not None:
        try:
            _ = json.loads(resp.output)
            format_valid = True
        except Exception:
            format_valid = False

    if format_valid is False:
        judge.score = min(judge.score, 0.2)

    metrics = compute_metrics(
        judge_score=judge.score,
        prompt_tokens=resp.prompt_tokens,
        completion_tokens=resp.completion_tokens,
        latency_ms=latency_ms,
        context_limit=prompt.context_limit,
        format_valid=format_valid,
    )

    judge_info = {
        "judge_score": judge.score,
        "judge_criteria": judge.criteria,
        "judge_reasoning": judge.reasoning,
    }
    return resp.output, metrics, judge_info
```

Replace the `run_dataset` signature and first few lines (lines 150–183) with:

```python
async def run_dataset(
    adapter: BaseAdapter,
    prompt: Prompt,
    testcases: list[TestCase],
    judge_model: str,
    mlflow_uri: str = "./mlruns",
    harness: EvalHarness | None = None,
) -> dict[str, Any]:
    if harness is None:
        harness = LLMJudgeHarness(adapter, judge_model)

    init_db()

    # Health check before running
    healthy = await adapter.health_check()
    if not healthy:
        raise RuntimeError("Model provider unreachable. Check that the service is running.")

    mlflow.set_tracking_uri(mlflow_uri)

    if mlflow.active_run():
        mlflow.end_run()

    with mlflow.start_run() as run:
        mlflow.log_params(
            {
                "prompt_name": prompt.name,
                "model": prompt.model,
                "provider": prompt.provider,
                "context_limit": prompt.context_limit,
                **prompt.params,
            }
        )

        tasks = [run_prompt(adapter, prompt, tc, judge_model, harness=harness) for tc in testcases]
        results = await asyncio.gather(*tasks)
```

The rest of `run_dataset` (aggregation, regression, storage) is unchanged.

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_runner_harness.py tests/test_harness.py tests/test_deepeval_harness.py -v
```

Expected: all 13 tests pass.

- [ ] **Step 5: Confirm existing tests still pass**

```bash
pytest tests/ -v
```

Expected: all existing tests still pass (judge, metrics, db, mutations).

---

## Task 7: app.py — eval_harness request field

**Files:**
- Modify: `promptops/api/app.py`

- [ ] **Step 1: Write the failing test**

Append a new file `tests/test_app_eval_harness.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from promptops.api.app import app

client = TestClient(app)

RUN_PAYLOAD = {
    "prompt": {
        "name": "test",
        "system": "You are helpful.",
        "template": "{input}",
        "model": "llama3.1",
        "params": {"temperature": 0.2, "max_tokens": 200},
        "context_limit": 4096,
        "provider": "ollama",
    },
    "judge_model": "llama3.1",
}

MOCK_RUN_RESULT = {
    "run_id": 1,
    "avg_judge_score": 0.8,
    "avg_objective": 0.75,
    "outputs": ["output"],
    "regression": False,
    "regression_warning": None,
}


def test_run_without_eval_harness_passes_none_harness():
    with patch("promptops.api.app.run_dataset", return_value=MOCK_RUN_RESULT) as mock_run:
        response = client.post("/run", json=RUN_PAYLOAD)

    assert response.status_code == 200
    call_kwargs = mock_run.call_args.kwargs
    assert call_kwargs.get("harness") is None


def test_run_with_deepeval_harness_constructs_deepeval_harness():
    payload = {**RUN_PAYLOAD, "eval_harness": "deepeval"}

    with patch("promptops.api.app.run_dataset", return_value=MOCK_RUN_RESULT) as mock_run, \
         patch("promptops.api.app.DeepEvalHarness") as MockDEH:
        mock_deh_instance = MagicMock()
        MockDEH.return_value = mock_deh_instance

        response = client.post("/run", json=payload)

    assert response.status_code == 200
    MockDEH.assert_called_once()
    call_kwargs = mock_run.call_args.kwargs
    assert call_kwargs.get("harness") is mock_deh_instance


def test_run_with_unknown_eval_harness_returns_400():
    payload = {**RUN_PAYLOAD, "eval_harness": "unknown_framework"}
    response = client.post("/run", json=payload)
    assert response.status_code == 400
```

- [ ] **Step 2: Run to confirm they fail**

```bash
pytest tests/test_app_eval_harness.py -v
```

Expected: all 3 fail — `RunRequest` doesn't have `eval_harness` yet.

- [ ] **Step 3: Modify `promptops/api/app.py`**

Add this import near the top of the file (after the existing imports, before `@asynccontextmanager`):

```python
from promptops.eval.deepeval_harness import DeepEvalHarness
```

Replace the `RunRequest` class (lines 68–72) with:

```python
class RunRequest(BaseModel):
    prompt: PromptPayload
    judge_model: str = "llama3.1"
    suite_id: int | None = None
    eval_harness: str | None = None
```

Replace the `run()` endpoint function (lines 136–157) with:

```python
@app.post("/run")
async def run(req: RunRequest) -> dict[str, Any]:
    if req.eval_harness is not None and req.eval_harness != "deepeval":
        raise HTTPException(status_code=400, detail=f"Unknown eval_harness: {req.eval_harness!r}. Supported: 'deepeval'")

    adapter = make_adapter(req.prompt.provider)
    prompt = Prompt(**req.prompt.model_dump())

    if req.suite_id is not None:
        suite_cases = get_suite_cases(req.suite_id)
        if not suite_cases:
            raise HTTPException(status_code=404, detail="Suite not found or has no cases")
        testcases = [
            TestCase(
                input=sc["input"],
                expected=sc.get("expected"),
                rubric=sc.get("rubric"),
            )
            for sc in suite_cases
        ]
    else:
        testcases = demo_dataset()

    harness = None
    if req.eval_harness == "deepeval":
        harness = DeepEvalHarness(adapter=adapter, model=req.judge_model)

    results = await run_dataset(adapter, prompt, testcases, req.judge_model, harness=harness)
    return results
```

- [ ] **Step 4: Run app harness tests**

```bash
pytest tests/test_app_eval_harness.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Run full test suite**

```bash
pytest tests/ -v
```

Expected: all tests pass.

---

## Task 8: pytest eval test suite

**Files:**
- Create: `promptops/tests/evals/__init__.py`
- Create: `promptops/tests/evals/conftest.py`
- Create: `promptops/tests/evals/test_prompt_quality.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: Register the `deepeval` pytest mark in `pyproject.toml`**

Add `markers` to the `[tool.pytest.ini_options]` section:

```toml
[tool.pytest.ini_options]
addopts = "-q"
markers = [
  "deepeval: marks tests as DeepEval integration evals (require Ollama running)",
]
```

- [ ] **Step 2: Create the package marker**

Create `promptops/tests/evals/__init__.py` as an empty file.

- [ ] **Step 3: Create `promptops/tests/evals/conftest.py`**

```python
from __future__ import annotations

import asyncio
import os
import pytest

from promptops.core.adapters.ollama import OllamaAdapter
from promptops.core.prompt import Prompt
from promptops.eval.deepeval_harness import PromptOpsDeepEvalLLM


async def _is_healthy(adapter: OllamaAdapter) -> bool:
    return await adapter.health_check()


@pytest.fixture(scope="session")
def adapter():
    url = os.getenv("OLLAMA_URL", "http://localhost:11434")
    a = OllamaAdapter(url)
    if not asyncio.run(_is_healthy(a)):
        pytest.skip("Ollama unreachable — start Ollama or set OLLAMA_URL to run eval tests")
    return a


@pytest.fixture(scope="session")
def default_prompt():
    return Prompt(
        name="eval_test_prompt",
        system="You are a helpful assistant.",
        template="{input}",
        model="llama3.1",
        params={"temperature": 0.2, "max_tokens": 200},
        context_limit=4096,
        provider="ollama",
    )


@pytest.fixture(scope="session")
def deepeval_llm(adapter, default_prompt):
    return PromptOpsDeepEvalLLM(adapter=adapter, model=default_prompt.model)


def generate_output(adapter, prompt: Prompt, text: str) -> str:
    """Synchronous helper: renders prompt, calls adapter, returns raw output string."""
    async def _run() -> str:
        rendered = prompt.render(input=text)
        resp = await adapter.generate(
            model=prompt.model,
            system=prompt.system,
            prompt=rendered,
            params=prompt.params,
        )
        return resp.output
    return asyncio.run(_run())
```

- [ ] **Step 4: Create `promptops/tests/evals/test_prompt_quality.py`**

```python
from __future__ import annotations

import pytest
from deepeval import assert_test
from deepeval.metrics import GEval, AnswerRelevancyMetric
from deepeval.test_case import LLMTestCase, LLMTestCaseParams

from promptops.tests.evals.conftest import generate_output


@pytest.mark.deepeval
def test_closure_explanation(adapter, default_prompt, deepeval_llm):
    output = generate_output(adapter, default_prompt, "Explain closures in Python in one sentence.")
    test_case = LLMTestCase(
        input="Explain closures in Python in one sentence.",
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


@pytest.mark.deepeval
def test_summarization(adapter, default_prompt, deepeval_llm):
    output = generate_output(
        adapter, default_prompt, "Summarize: The cat sat on the mat and purred."
    )
    test_case = LLMTestCase(
        input="Summarize: The cat sat on the mat and purred.",
        actual_output=output,
        expected_output="A cat sat on a mat and purred.",
    )
    assert_test(test_case, [
        GEval(
            name="Coverage",
            criteria="Does the output cover the key facts from the input without adding hallucinations?",
            evaluation_params=[
                LLMTestCaseParams.INPUT,
                LLMTestCaseParams.ACTUAL_OUTPUT,
                LLMTestCaseParams.EXPECTED_OUTPUT,
            ],
            model=deepeval_llm,
            threshold=0.5,
        ),
        AnswerRelevancyMetric(model=deepeval_llm, threshold=0.5),
    ])
```

- [ ] **Step 5: Verify the eval tests are collected correctly**

```bash
pytest promptops/tests/evals/ --collect-only -q
```

Expected output lists `test_closure_explanation` and `test_summarization` under `promptops/tests/evals/test_prompt_quality.py`.

- [ ] **Step 6: Run eval tests (requires Ollama running with llama3.1 pulled)**

```bash
pytest -m deepeval promptops/tests/evals/ -v
```

Expected: 2 passed. If Ollama is not running, both tests are skipped (not failed) — the fixture calls `pytest.skip()` automatically.

- [ ] **Step 7: Confirm unit tests are unaffected**

```bash
pytest tests/ -v
```

Expected: all unit tests pass, no regressions.

---

## Completion Checklist

- [ ] `deepeval` installs cleanly: `python -c "import deepeval"`
- [ ] `EvalHarness` is abstract and cannot be instantiated directly
- [ ] `LLMJudgeHarness.evaluate()` delegates to `judge_output()` with correct kwargs
- [ ] `PromptOpsDeepEvalLLM.a_generate()` routes through `BaseAdapter.generate()` with no OpenAI calls
- [ ] `DeepEvalHarness.evaluate()` returns a `JudgeResult` with averaged metric scores
- [ ] `run_prompt(harness=None)` defaults to `LLMJudgeHarness` — existing tests pass
- [ ] `run_dataset(harness=mock)` passes mock through to `run_prompt`
- [ ] `POST /run` without `eval_harness` → `harness=None` → `LLMJudgeHarness` (unchanged behaviour)
- [ ] `POST /run` with `eval_harness="deepeval"` → `DeepEvalHarness` constructed and used
- [ ] `POST /run` with unknown `eval_harness` → 400 error
- [ ] `pytest -m deepeval` runs and skips gracefully when Ollama is unavailable
- [ ] All existing unit tests (`tests/`) continue to pass
