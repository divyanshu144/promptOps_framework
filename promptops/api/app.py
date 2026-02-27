from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from promptops.core.adapters import make_adapter
from promptops.core.prompt import Prompt
from promptops.core.runner import run_dataset, run_prompt_detailed
from promptops.opt.optimizer import optimize_prompt
from promptops.tests.dataset import demo_dataset
from promptops.tests.testcase import TestCase
from promptops.store.db import (
    top_runs,
    recent_runs,
    init_db,
    get_run,
    get_run_results,
    list_suites,
    get_suite,
    create_suite,
    delete_suite,
    get_suite_cases,
    add_suite_case,
    remove_suite_case,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="PromptOps", lifespan=lifespan)

origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PromptPayload(BaseModel):
    name: str = "demo_prompt"
    system: str = "You are a helpful assistant."
    template: str = "{input}"
    model: str = "llama3.1"
    params: dict[str, Any] = Field(default_factory=lambda: {"temperature": 0.2, "max_tokens": 200})
    context_limit: int = 4096
    output_format: str | None = None
    output_schema: dict[str, Any] | None = None
    provider: str = "ollama"


class RunRequest(BaseModel):
    prompt: PromptPayload
    judge_model: str = "llama3.1"
    suite_id: int | None = None


class PreviewRequest(BaseModel):
    prompt: PromptPayload | None = None
    prompts: list[PromptPayload] | None = None
    judge_model: str = "llama3.1"
    inputs: list[str] | None = None
    rubric: dict[str, Any] | None = None

    @field_validator("inputs")
    @classmethod
    def validate_inputs(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        if len(v) > 20:
            raise ValueError("inputs: max 20 items allowed")
        for item in v:
            if len(item) > 2000:
                raise ValueError("inputs: each item must be at most 2000 characters")
        return v


class OptimizeRequest(BaseModel):
    prompt: PromptPayload
    judge_model: str = "llama3.1"
    iterations: int = 2
    use_rewriter: bool = True
    rewriter_model: str | None = None

    @field_validator("iterations")
    @classmethod
    def clamp_iterations(cls, v: int) -> int:
        return max(1, min(5, v))


class SuiteCreateRequest(BaseModel):
    name: str
    description: str | None = None
    cases: list[dict[str, Any]] = Field(default_factory=list)


class SuiteCaseRequest(BaseModel):
    input: dict[str, Any]
    expected: str | None = None
    rubric: dict[str, Any] | None = None
    order_idx: int = 0


@app.get("/")
def root() -> dict[str, Any]:
    return {"status": "ok"}


@app.get("/health")
async def health(provider: str = "ollama") -> dict[str, Any]:
    try:
        adapter = make_adapter(provider)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    ok = await adapter.health_check()
    return {"status": "ok" if ok else "unreachable", "provider": provider}


@app.post("/run")
async def run(req: RunRequest) -> dict[str, Any]:
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

    results = await run_dataset(adapter, prompt, testcases, req.judge_model)
    return results


@app.post("/preview")
async def preview(req: PreviewRequest) -> dict[str, Any]:
    prompt_payloads = req.prompts or ([req.prompt] if req.prompt else [])
    prompts = [Prompt(**p.model_dump()) for p in prompt_payloads]

    if req.inputs:
        testcases = [TestCase(input={"input": text}, rubric=req.rubric) for text in req.inputs]
    else:
        testcases = demo_dataset()

    all_results = []
    for prompt in prompts:
        adapter = make_adapter(prompt.provider)
        prompt_results = []
        for tc in testcases:
            prompt_results.append(
                await run_prompt_detailed(adapter, prompt, tc, req.judge_model)
            )
        all_results.append({"prompt": prompt.model_dump(), "results": prompt_results})

    return {"results": all_results}


@app.post("/optimize")
async def optimize(req: OptimizeRequest) -> dict[str, Any]:
    adapter = make_adapter(req.prompt.provider)
    prompt = Prompt(**req.prompt.model_dump())
    results = await optimize_prompt(
        adapter=adapter,
        base_prompt=prompt,
        testcases=demo_dataset(),
        judge_model=req.judge_model,
        iterations=req.iterations,
        use_rewriter=req.use_rewriter,
        rewriter_model=req.rewriter_model,
    )
    return {
        "best_prompt": results["best_prompt"].model_dump(),
        "best_result": results["best_result"],
    }


@app.get("/leaderboard")
def leaderboard() -> dict[str, Any]:
    return {"runs": top_runs(10)}


@app.get("/runs")
def runs(limit: int = 200) -> dict[str, Any]:
    return {"runs": recent_runs(limit)}


@app.get("/runs/{run_id}")
def run_detail(run_id: int) -> dict[str, Any]:
    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="not_found")
    results = get_run_results(run_id)
    return {"run": run, "results": results}


# --- Suite endpoints ---

@app.get("/suites")
def list_suites_endpoint() -> dict[str, Any]:
    return {"suites": list_suites()}


@app.post("/suites")
def create_suite_endpoint(req: SuiteCreateRequest) -> dict[str, Any]:
    suite_id = create_suite(req.name, req.description)
    for idx, case in enumerate(req.cases):
        add_suite_case(
            suite_id=suite_id,
            input_data=case.get("input", {}),
            expected=case.get("expected"),
            rubric=case.get("rubric"),
            order_idx=idx,
        )
    suite = get_suite(suite_id)
    cases = get_suite_cases(suite_id)
    return {"suite": suite, "cases": cases}


@app.get("/suites/{suite_id}")
def get_suite_endpoint(suite_id: int) -> dict[str, Any]:
    suite = get_suite(suite_id)
    if not suite:
        raise HTTPException(status_code=404, detail="not_found")
    cases = get_suite_cases(suite_id)
    return {"suite": suite, "cases": cases}


@app.delete("/suites/{suite_id}")
def delete_suite_endpoint(suite_id: int) -> dict[str, Any]:
    suite = get_suite(suite_id)
    if not suite:
        raise HTTPException(status_code=404, detail="not_found")
    delete_suite(suite_id)
    return {"deleted": suite_id}


@app.post("/suites/{suite_id}/cases")
def add_suite_case_endpoint(suite_id: int, req: SuiteCaseRequest) -> dict[str, Any]:
    suite = get_suite(suite_id)
    if not suite:
        raise HTTPException(status_code=404, detail="not_found")
    case_id = add_suite_case(
        suite_id=suite_id,
        input_data=req.input,
        expected=req.expected,
        rubric=req.rubric,
        order_idx=req.order_idx,
    )
    return {"case_id": case_id}


@app.delete("/suites/{suite_id}/cases/{case_id}")
def remove_suite_case_endpoint(suite_id: int, case_id: int) -> dict[str, Any]:
    remove_suite_case(case_id)
    return {"deleted": case_id}
