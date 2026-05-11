import pytest
import promptops.store.db as db_module
from promptops.store.db import (
    init_db,
    insert_run,
    get_run,
    insert_run_result,
    get_run_results,
    get_best_for_prompt,
    get_prompt_history,
    list_prompt_names,
    recent_runs,
    top_runs,
    create_suite,
    get_suite,
    delete_suite,
    list_suites,
    add_suite_case,
    get_suite_cases,
    remove_suite_case,
)


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    monkeypatch.setattr(db_module, "DB_PATH", db_file)
    init_db()


def _run(**kwargs) -> dict:
    base = {
        "prompt_name": "test_prompt",
        "prompt_hash": "abc123",
        "model": "llama3.1",
        "run_id": "mlflow-1",
        "mlflow_uri": "./mlruns",
        "judge_score": 0.8,
        "objective": 0.75,
        "prompt_tokens": 100,
        "completion_tokens": 50,
        "total_tokens": 150,
        "latency_ms": 300.0,
        "context_window_used": 0.037,
        "regression": False,
    }
    base.update(kwargs)
    return base


def test_insert_and_get_run():
    rid = insert_run(_run())
    r = get_run(rid)
    assert r is not None
    assert r["prompt_name"] == "test_prompt"
    assert r["objective"] == pytest.approx(0.75)


def test_get_run_missing_returns_none():
    assert get_run(9999) is None


def test_regression_flag_stored_as_1():
    rid = insert_run(_run(regression=True))
    assert get_run(rid)["regression"] == 1


def test_regression_flag_false_stored_as_0():
    rid = insert_run(_run(regression=False))
    assert get_run(rid)["regression"] == 0


def test_get_best_for_prompt_picks_highest_objective():
    insert_run(_run(objective=0.5))
    insert_run(_run(objective=0.9))
    insert_run(_run(objective=0.7))
    best = get_best_for_prompt("test_prompt")
    assert best["objective"] == pytest.approx(0.9)


def test_get_best_for_prompt_returns_none_when_missing():
    assert get_best_for_prompt("nonexistent") is None


def test_insert_run_result_round_trips_json():
    rid = insert_run(_run())
    insert_run_result(
        run_id=rid,
        test_idx=0,
        input_data={"input": "hello"},
        expected="world",
        output="Hello world!",
        judge_score=0.8,
        judge_criteria={"quality": 0.8},
        judge_reasoning="Good response",
        metrics={"objective": 0.75},
    )
    results = get_run_results(rid)
    assert len(results) == 1
    r = results[0]
    assert r["output"] == "Hello world!"
    assert r["input"] == {"input": "hello"}
    assert r["judge_criteria"] == {"quality": 0.8}
    assert r["expected"] == "world"


def test_get_prompt_history_ordered_asc():
    insert_run(_run(objective=0.5))
    insert_run(_run(objective=0.9))
    history = get_prompt_history("test_prompt")
    assert len(history) == 2
    objectives = [r["objective"] for r in history]
    assert 0.5 in objectives and 0.9 in objectives


def test_get_prompt_history_empty_for_unknown():
    assert get_prompt_history("unknown") == []


def test_list_prompt_names_aggregates():
    insert_run(_run(prompt_name="alpha", objective=0.6))
    insert_run(_run(prompt_name="alpha", objective=0.8))
    insert_run(_run(prompt_name="beta", objective=0.5))
    names = list_prompt_names()
    assert len(names) == 2
    alpha = next(n for n in names if n["prompt_name"] == "alpha")
    assert alpha["run_count"] == 2
    assert alpha["best_objective"] == pytest.approx(0.8)


def test_recent_runs_returns_correct_count():
    insert_run(_run())
    insert_run(_run())
    assert len(recent_runs(10)) == 2


def test_top_runs_ordered_by_objective():
    insert_run(_run(objective=0.3))
    insert_run(_run(objective=0.9))
    insert_run(_run(objective=0.6))
    top = top_runs(2)
    assert len(top) == 2
    assert top[0]["objective"] == pytest.approx(0.9)


def test_suite_full_crud():
    sid = create_suite("my-suite", "a test suite")
    suite = get_suite(sid)
    assert suite["name"] == "my-suite"
    assert suite["description"] == "a test suite"

    cid1 = add_suite_case(sid, {"input": "q1"}, expected="a1", rubric={"quality": 1.0})
    add_suite_case(sid, {"input": "q2"})
    cases = get_suite_cases(sid)
    assert len(cases) == 2
    assert cases[0]["input"] == {"input": "q1"}
    assert cases[0]["rubric"] == {"quality": 1.0}
    assert cases[1]["rubric"] is None

    remove_suite_case(cid1)
    assert len(get_suite_cases(sid)) == 1

    suites = list_suites()
    assert any(s["id"] == sid for s in suites)

    delete_suite(sid)
    assert get_suite(sid) is None
    assert get_suite_cases(sid) == []
