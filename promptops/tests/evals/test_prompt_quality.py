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
