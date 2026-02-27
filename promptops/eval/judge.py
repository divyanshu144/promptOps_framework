from __future__ import annotations

import asyncio
import json
import re
from typing import Any, Dict

from pydantic import BaseModel

from promptops.core.adapters.base import BaseAdapter


class JudgeResult(BaseModel):
    score: float
    criteria: Dict[str, float] = {}
    reasoning: str | None = None


JUDGE_PROMPT = """
You are a strict evaluator. Score the assistant output using the rubric criteria.
Return JSON only with this exact structure:
{{"criteria": {{"<criterion>": <score 0.0-1.0>, ...}}, "overall": <float 0.0-1.0>, "reasoning": "<brief reasoning>"}}

Rubric: {rubric}
User Input: {user_input}
Assistant Output: {assistant_output}
{expected_section}
""".strip()


async def _single_judge_call(
    adapter: BaseAdapter,
    model: str,
    rubric: Dict[str, Any],
    user_input: Dict[str, Any],
    assistant_output: str,
    expected: str | None = None,
) -> JudgeResult:
    expected_section = ""
    if expected:
        expected_section = f"Expected Output: {expected}"

    prompt = JUDGE_PROMPT.format(
        rubric=json.dumps(rubric),
        user_input=json.dumps(user_input),
        assistant_output=assistant_output,
        expected_section=expected_section,
    )

    resp = await adapter.generate(
        model=model,
        system="You evaluate outputs and return JSON only.",
        prompt=prompt,
        params={"temperature": 0.0, "max_tokens": 300},
    )

    text = resp.output.strip()
    try:
        if not text.startswith("{"):
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                text = text[start : end + 1]
        data = json.loads(text)
        overall = float(data.get("overall", data.get("score", 0.0)))
        criteria = {k: float(v) for k, v in data.get("criteria", {}).items()}
        reasoning = data.get("reasoning")
        return JudgeResult(score=overall, criteria=criteria, reasoning=reasoning)
    except Exception:
        # Fallback: try to extract a float score from the raw text
        match = re.search(r"([01](?:\.\d+)?)", resp.output)
        if match:
            try:
                score = float(match.group(1))
                return JudgeResult(score=score, criteria={}, reasoning="Parsed score from non-JSON output")
            except Exception:
                pass
        return JudgeResult(score=0.0, criteria={}, reasoning="Failed to parse judge output")


async def judge_output(
    adapter: BaseAdapter,
    model: str,
    rubric: Dict[str, Any],
    user_input: Dict[str, Any],
    assistant_output: str,
    expected: str | None = None,
) -> JudgeResult:
    """Call judge 3× concurrently and average the results for stability."""
    results = await asyncio.gather(
        _single_judge_call(adapter, model, rubric, user_input, assistant_output, expected),
        _single_judge_call(adapter, model, rubric, user_input, assistant_output, expected),
        _single_judge_call(adapter, model, rubric, user_input, assistant_output, expected),
    )

    avg_score = sum(r.score for r in results) / 3.0

    # Average per-criterion scores
    all_criteria: Dict[str, list[float]] = {}
    for r in results:
        for k, v in r.criteria.items():
            all_criteria.setdefault(k, []).append(v)
    avg_criteria = {k: sum(vs) / len(vs) for k, vs in all_criteria.items()}

    # Use reasoning from the first successful result
    reasoning = next((r.reasoning for r in results if r.reasoning), None)

    return JudgeResult(score=avg_score, criteria=avg_criteria, reasoning=reasoning)
