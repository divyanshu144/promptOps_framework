from __future__ import annotations

from typing import Any

from promptops.core.adapter import OllamaAdapter
from promptops.core.prompt import Prompt


REWRITE_PROMPT = """
You are an expert prompt engineer. Rewrite the prompt to improve quality while reducing tokens.
Return JSON only: {"system": "...", "template": "..."}
Constraints:
- Keep the same intent and inputs
- Avoid extra verbosity
- Use the same input placeholders
Current system:
{system}
Current template:
{template}
""".strip()


async def rewrite_prompt(
    adapter: OllamaAdapter,
    model: str,
    prompt: Prompt,
) -> Prompt | None:
    text = REWRITE_PROMPT.format(system=prompt.system, template=prompt.template)
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
        data: dict[str, Any] = __import__("json").loads(raw)
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
