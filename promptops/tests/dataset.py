from __future__ import annotations

from .testcase import TestCase


def demo_dataset() -> list[TestCase]:
    return [
        TestCase(
            input={"input": "Explain what a closure is in Python in one sentence."},
            expected=None,
            rubric={"factuality": 0.5, "brevity": 0.5},
        ),
        TestCase(
            input={"input": "Summarize: The cat sat on the mat and purred."},
            expected=None,
            rubric={"coverage": 0.5, "brevity": 0.5},
        ),
    ]
