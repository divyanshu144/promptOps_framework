from __future__ import annotations

import json
from typing import Any

from promptops.core.adapters.base import BaseAdapter
from promptops.core.prompt import Prompt


REWRITE_PROMPT = """
You are an expert prompt engineer. Rewrite the prompt to improve quality while reducing tokens.
Return JSON only: {{"system": "...", "template": "..."}}
Constraints:
- Keep the same intent and inputs
- Avoid extra verbosity
- Use the same input placeholders
Current system:
{system}
Current template:
{template}
{feedback_section}
""".strip()


async def rewrite_prompt(
    adapter: BaseAdapter,
    model: str,
    prompt: Prompt,
    current_score: float | None = None,
    judge_reasoning: str | None = None,
) -> Prompt | None:
    feedback_lines: list[str] = []
    if current_score is not None:
        feedback_lines.append(f"Current avg judge score: {current_score:.2f}")
    if judge_reasoning:
        feedback_lines.append(f"Judge feedback sample: {judge_reasoning}")
    feedback_section = "\n".join(feedback_lines)

    text = REWRITE_PROMPT.format(
        system=prompt.system,
        template=prompt.template,
        feedback_section=feedback_section,
    )
    resp = await adapter.generate(
        model=model,
        system="Return JSON only.",
        prompt=text,
        params={"temperature": 0.2, "max_tokens": 300},
    )
    raw = resp.output.strip()
    try:
        if not raw.startswith("{"):
            start = raw.find("{")
            end = raw.rfind("}")
            if start != -1 and end != -1 and end > start:
                raw = raw[start : end + 1]
        data: dict[str, Any] = json.loads(raw)
        system = str(data.get("system", "")).strip()
        template = str(data.get("template", "")).strip()
        if not system or not template:
            return None
        variant = prompt.model_copy(deep=True)
        variant.name = f"{prompt.name}_rewrite"
        variant.system = system
        variant.template = template
        return variant
    except Exception:
        return None
