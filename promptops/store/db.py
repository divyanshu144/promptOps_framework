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
            ("run_results", "passed", "INTEGER"),
            ("suite_cases", "threshold", "REAL DEFAULT 0.7"),
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
                context_window_used, regression
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            d["input"] = json.loads(d["input"]) if d["input"] else {}
            d["metrics"] = json.loads(d["metrics"]) if d["metrics"] else {}
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
        return dict(row) if row else None


def get_prompt_history(prompt_name: str, limit: int = 100) -> list[dict[str, Any]]:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM runs WHERE prompt_name = ? ORDER BY created_at ASC LIMIT ?",
            (prompt_name, limit),
        )
        return [dict(row) for row in cur.fetchall()]


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
        return [dict(row) for row in cur.fetchall()]


def recent_runs(limit: int = 50) -> list[dict[str, Any]]:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM runs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in cur.fetchall()]


def get_run(run_id: int) -> dict[str, Any] | None:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
        row = cur.fetchone()
        return dict(row) if row else None


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
            results.append(d)
        return results


def add_suite_case(
    suite_id: int,
    input_data: dict[str, Any],
    expected: str | None = None,
    rubric: dict[str, Any] | None = None,
    threshold: float = 0.7,
    order_idx: int = 0,
) -> int:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO suite_cases (suite_id, input, expected, rubric, threshold, order_idx) VALUES (?, ?, ?, ?, ?, ?)",
            (
                suite_id,
                json.dumps(input_data),
                expected,
                json.dumps(rubric) if rubric else None,
                threshold,
                order_idx,
            ),
        )
        return cur.lastrowid  # type: ignore[return-value]


def remove_suite_case(case_id: int) -> None:
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM suite_cases WHERE id = ?", (case_id,))
