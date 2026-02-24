from __future__ import annotations

import json
from typing import Any, Dict
from pydantic import BaseModel

from promptops.core.adapter import OllamaAdapter


class JudgeResult(BaseModel):
    score: float
    reasoning: str | None = None


JUDGE_PROMPT = """
You are a strict evaluator. Score the assistant output from 0.0 to 1.0 using the rubric.
Return JSON only: {{"score": float, "reasoning": "..."}}
Rubric: {rubric}
User Input: {user_input}
Assistant Output: {assistant_output}
""".strip()


async def judge_output(
    adapter: OllamaAdapter,
    model: str,
    rubric: Dict[str, Any],
    user_input: Dict[str, Any],
    assistant_output: str,
) -> JudgeResult:
    prompt = JUDGE_PROMPT.format(
        rubric=json.dumps(rubric),
        user_input=json.dumps(user_input),
        assistant_output=assistant_output,
    )

    resp = await adapter.generate(
        model=model,
        system="You evaluate outputs and return JSON only.",
        prompt=prompt,
        params={"temperature": 0.0, "max_tokens": 200},
    )

    text = resp.output.strip()
    try:
        if not text.startswith("{"):
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                text = text[start : end + 1]
        data = json.loads(text)
        score = float(data.get("score", 0.0))
        reasoning = data.get("reasoning")
        return JudgeResult(score=score, reasoning=reasoning)
    except Exception:
        # Fallback: try to extract a float score from the raw text
        import re

        match = re.search(r"([01](?:\\.\\d+)?)", resp.output)
        if match:
            try:
                score = float(match.group(1))
                return JudgeResult(score=score, reasoning="Parsed score from non-JSON output")
            except Exception:
                pass
        return JudgeResult(score=0.0, reasoning="Failed to parse judge output")
