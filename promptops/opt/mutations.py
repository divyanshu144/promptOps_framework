from __future__ import annotations

from copy import deepcopy
from typing import Iterable

from promptops.core.prompt import Prompt


def basic_mutations(prompt: Prompt) -> Iterable[Prompt]:
    variants: list[Prompt] = []

    # Concise system variant
    p1 = deepcopy(prompt)
    p1.name = f"{prompt.name}_concise"
    p1.system = prompt.system + " Be concise and avoid filler."
    variants.append(p1)

    # Explicit formatting variant
    p2 = deepcopy(prompt)
    p2.name = f"{prompt.name}_format"
    p2.system = prompt.system + " Respond in 1-3 sentences."
    variants.append(p2)

    # JSON output variant
    p3 = deepcopy(prompt)
    p3.name = f"{prompt.name}_json"
    p3.system = prompt.system + " Output JSON with keys: answer."
    p3.output_format = "json"
    variants.append(p3)

    # Bullet list variant
    p4 = deepcopy(prompt)
    p4.name = f"{prompt.name}_bullets"
    p4.system = prompt.system + " Use short bullet points."
    variants.append(p4)

    # Final-answer-only variant
    p5 = deepcopy(prompt)
    p5.name = f"{prompt.name}_finalonly"
    p5.system = prompt.system + " Provide only the final answer."
    variants.append(p5)

    # Few-shot injection variant
    p6 = deepcopy(prompt)
    p6.name = f"{prompt.name}_fewshot"
    p6.template = (
        "Examples:\n"
        "Input: What is 2+2?\n"
        "Output: 4\n\n"
        "Input: Define recursion briefly.\n"
        "Output: Recursion is a function calling itself.\n\n"
        "Task:\n"
        "{input}\n"
    )
    variants.append(p6)

    # Schema enforcement variant
    p7 = deepcopy(prompt)
    p7.name = f"{prompt.name}_schema"
    p7.system = prompt.system + " Respond with JSON matching this schema: {\"answer\": string}"
    p7.output_format = "json"
    p7.output_schema = {"answer": "string"}
    variants.append(p7)

    # Lower max_tokens variant if present
    if "max_tokens" in prompt.params:
        p8 = deepcopy(prompt)
        p8.name = f"{prompt.name}_lowtokens"
        p8.params["max_tokens"] = max(32, int(prompt.params["max_tokens"] * 0.7))
        variants.append(p8)

    return variants
