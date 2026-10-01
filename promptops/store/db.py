from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

DB_PATH = Path(os.getenv("PROMPTOPS_DB", "./promptops.db"))


@contextmanager
def _conn() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with _conn() as conn:
        cur = conn.cursor()

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_name TEXT NOT NULL,
                prompt_hash TEXT NOT NULL,
                model TEXT NOT NULL,
                run_id TEXT,
                mlflow_uri TEXT,
                judge_score REAL,
                objective REAL,
                pass_rate REAL,
                prompt_tokens INTEGER,
                completion_tokens INTEGER,
                total_tokens INTEGER,
                latency_ms REAL,
                context_window_used REAL,
                regression INTEGER DEFAULT 0,
                suite_id INTEGER,
                eval_harness TEXT,
                release_label TEXT,
                gate_status TEXT,
                aggregate_metrics TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS run_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
                test_idx INTEGER NOT NULL,
                input TEXT NOT NULL,
                expected TEXT,
                output TEXT NOT NULL,
                judge_score REAL,
                judge_criteria TEXT,
                judge_reasoning TEXT,
                metrics TEXT NOT NULL,
                passed INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS suites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS suite_cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                suite_id INTEGER NOT NULL REFERENCES suites(id) ON DELETE CASCADE,
                input TEXT NOT NULL,
                expected TEXT,
                rubric TEXT,
                threshold REAL DEFAULT 0.7,
                order_idx INTEGER DEFAULT 0
            );
            """
        )

        # Best-effort migrations for existing DBs
        for table, col, col_type in [
            ("runs", "run_id", "TEXT"),
            ("runs", "mlflow_uri", "TEXT"),
            ("runs", "regression", "INTEGER DEFAULT 0"),
            ("runs", "pass_rate", "REAL"),
            ("runs", "suite_id", "INTEGER"),
            ("runs", "eval_harness", "TEXT"),
            ("runs", "release_label", "TEXT"),
            ("runs", "gate_status", "TEXT"),
            ("runs", "aggregate_metrics", "TEXT"),
            ("run_results", "passed", "INTEGER"),
            ("suite_cases", "threshold", "REAL DEFAULT 0.7"),
            ("suite_cases", "expected_tools", "TEXT"),
            ("suite_cases", "relevant_doc_ids", "TEXT"),
            ("suite_cases", "expected_claims", "TEXT"),
        ]:
            try:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
            except sqlite3.OperationalError:
                pass


def insert_run(data: dict[str, Any]) -> int:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO runs (
                prompt_name, prompt_hash, model, run_id, mlflow_uri, judge_score, objective,
                pass_rate, prompt_tokens, completion_tokens, total_tokens, latency_ms,
                context_window_used, regression, suite_id, eval_harness, release_label,
                gate_status, aggregate_metrics
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["prompt_name"],
                data["prompt_hash"],
                data["model"],
                data.get("run_id"),
                data.get("mlflow_uri"),
                data.get("judge_score"),
                data.get("objective"),
                data.get("pass_rate"),
                data.get("prompt_tokens"),
                data.get("completion_tokens"),
                data.get("total_tokens"),
                data.get("latency_ms"),
                data.get("context_window_used"),
                1 if data.get("regression") else 0,
                data.get("suite_id"),
                data.get("eval_harness"),
                data.get("release_label"),
                data.get("gate_status"),
                json.dumps(data.get("aggregate_metrics")) if data.get("aggregate_metrics") else None,
            ),
        )
        return cur.lastrowid  # type: ignore[return-value]


def insert_run_result(
    run_id: int,
    test_idx: int,
    input_data: dict[str, Any],
    expected: str | None,
    output: str,
    judge_score: float | None,
    judge_criteria: dict[str, float] | None,
    judge_reasoning: str | None,
    metrics: dict[str, Any],
    passed: bool | None = None,
) -> None:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO run_results (
                run_id, test_idx, input, expected, output,
                judge_score, judge_criteria, judge_reasoning, metrics, passed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                test_idx,
                json.dumps(input_data),
                expected,
                output,
                judge_score,
                json.dumps(judge_criteria) if judge_criteria else None,
                judge_reasoning,
                json.dumps(metrics),
                1 if passed else 0 if passed is not None else None,
            ),
        )


def get_run_results(run_id: int) -> list[dict[str, Any]]:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM run_results WHERE run_id = ? ORDER BY test_idx",
            (run_id,),
        )
        results = []
        for row in cur.fetchall():
            d = dict(row)
            if d.get("aggregate_metrics"):
                d["aggregate_metrics"] = json.loads(d["aggregate_metrics"])
            d["input"] = json.loads(d["input"]) if d["input"] else {}
            d["metrics"] = json.loads(d["metrics"]) if d["metrics"] else {}
            d["failure_labels"] = d["metrics"].get("failure_labels", [])
            d["judge_criteria"] = json.loads(d["judge_criteria"]) if d["judge_criteria"] else {}
            results.append(d)
        return results


def get_best_for_prompt(prompt_name: str) -> dict[str, Any] | None:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM runs WHERE prompt_name = ? ORDER BY objective DESC LIMIT 1",
            (prompt_name,),
        )
        row = cur.fetchone()
        if not row:
            return None
        data = dict(row)
        if data.get("aggregate_metrics"):
            data["aggregate_metrics"] = json.loads(data["aggregate_metrics"])
        return data


def get_prompt_history(prompt_name: str, limit: int = 100) -> list[dict[str, Any]]:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM runs WHERE prompt_name = ? ORDER BY created_at ASC LIMIT ?",
            (prompt_name, limit),
        )
        return [_decode_run_row(row) for row in cur.fetchall()]


def list_prompt_names() -> list[dict[str, Any]]:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                prompt_name,
                COUNT(*) AS run_count,
                MAX(objective) AS best_objective,
                AVG(objective) AS avg_objective,
                MAX(created_at) AS last_run_at
            FROM runs
            GROUP BY prompt_name
            ORDER BY last_run_at DESC
            """
        )
        return [dict(row) for row in cur.fetchall()]


def top_runs(limit: int = 10) -> list[dict[str, Any]]:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM runs ORDER BY objective DESC LIMIT ?",
            (limit,),
        )
        return [_decode_run_row(row) for row in cur.fetchall()]


def recent_runs(limit: int = 50) -> list[dict[str, Any]]:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM runs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        return [_decode_run_row(row) for row in cur.fetchall()]


def get_run(run_id: int) -> dict[str, Any] | None:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
        row = cur.fetchone()
        return _decode_run_row(row) if row else None


def _decode_run_row(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    if data.get("aggregate_metrics"):
        data["aggregate_metrics"] = json.loads(data["aggregate_metrics"])
    return data


def update_run_gate(run_id: int, gate_status: str) -> None:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE runs SET gate_status = ? WHERE id = ?", (gate_status, run_id))


# --- Suite CRUD ---

def list_suites() -> list[dict[str, Any]]:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT s.*, COUNT(sc.id) AS case_count
            FROM suites s
            LEFT JOIN suite_cases sc ON sc.suite_id = s.id
            GROUP BY s.id
            ORDER BY s.created_at DESC
            """
        )
        return [dict(row) for row in cur.fetchall()]


def get_suite(suite_id: int) -> dict[str, Any] | None:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM suites WHERE id = ?", (suite_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def create_suite(name: str, description: str | None = None) -> int:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO suites (name, description) VALUES (?, ?)",
            (name, description),
        )
        return cur.lastrowid  # type: ignore[return-value]


def delete_suite(suite_id: int) -> None:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM suites WHERE id = ?", (suite_id,))


def get_suite_cases(suite_id: int) -> list[dict[str, Any]]:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM suite_cases WHERE suite_id = ? ORDER BY order_idx, id",
            (suite_id,),
        )
        results = []
        for row in cur.fetchall():
            d = dict(row)
            d["input"] = json.loads(d["input"]) if d["input"] else {}
            d["rubric"] = json.loads(d["rubric"]) if d["rubric"] else None
            d["expected_tools"] = json.loads(d["expected_tools"]) if d.get("expected_tools") else None
            d["relevant_doc_ids"] = json.loads(d["relevant_doc_ids"]) if d.get("relevant_doc_ids") else None
            d["expected_claims"] = json.loads(d["expected_claims"]) if d.get("expected_claims") else None
            results.append(d)
        return results


def add_suite_case(
    suite_id: int,
    input_data: dict[str, Any],
    expected: str | None = None,
    rubric: dict[str, Any] | None = None,
    threshold: float = 0.7,
    order_idx: int = 0,
    expected_tools: list[str] | None = None,
    relevant_doc_ids: list[str] | None = None,
    expected_claims: list[str] | None = None,
) -> int:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO suite_cases (
                suite_id, input, expected, rubric, threshold, order_idx,
                expected_tools, relevant_doc_ids, expected_claims
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                suite_id,
                json.dumps(input_data),
                expected,
                json.dumps(rubric) if rubric else None,
                threshold,
                order_idx,
                json.dumps(expected_tools) if expected_tools else None,
                json.dumps(relevant_doc_ids) if relevant_doc_ids else None,
                json.dumps(expected_claims) if expected_claims else None,
            ),
        )
        return cur.lastrowid  # type: ignore[return-value]


def remove_suite_case(case_id: int) -> None:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM suite_cases WHERE id = ?", (case_id,))
