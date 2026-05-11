import pytest
from promptops.core.prompt import Prompt
from promptops.opt.mutations import basic_mutations
from promptops.tests.testcase import TestCase


def _prompt(**kwargs) -> Prompt:
    base = dict(
        name="base",
        system="You are helpful.",
        template="{input}",
        model="llama3.1",
        params={"temperature": 0.2, "max_tokens": 200},
    )
    base.update(kwargs)
    return Prompt(**base)


def test_count_with_max_tokens():
    variants = list(basic_mutations(_prompt()))
    assert len(variants) == 8


def test_count_without_max_tokens():
    p = _prompt(params={"temperature": 0.2})
    variants = list(basic_mutations(p))
    assert len(variants) == 7


def test_all_variant_names_present():
    variants = list(basic_mutations(_prompt()))
    names = {v.name for v in variants}
    for suffix in ("_concise", "_format", "_json", "_bullets", "_finalonly", "_fewshot", "_schema"):
        assert f"base{suffix}" in names


def test_lowtokens_reduces_max_tokens():
    variants = list(basic_mutations(_prompt()))
    lt = next(v for v in variants if v.name == "base_lowtokens")
    assert lt.params["max_tokens"] < 200
    assert lt.params["max_tokens"] >= 32


def test_fewshot_injects_testcase_examples():
    tc = TestCase(input={"input": "What is 2+2?"}, expected="4")
    variants = list(basic_mutations(_prompt(), testcases=[tc]))
    fewshot = next(v for v in variants if v.name == "base_fewshot")
    assert "4" in fewshot.template


def test_fewshot_fallback_without_testcases():
    variants = list(basic_mutations(_prompt(), testcases=[]))
    fewshot = next(v for v in variants if v.name == "base_fewshot")
    assert "{input}" in fewshot.template


def test_mutations_do_not_modify_original():
    original = _prompt()
    original_system = original.system
    list(basic_mutations(original))
    assert original.system == original_system


def test_json_variants_set_output_format():
    variants = list(basic_mutations(_prompt()))
    json_v = next(v for v in variants if v.name == "base_json")
    assert json_v.output_format == "json"
