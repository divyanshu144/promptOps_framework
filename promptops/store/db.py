from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = Path(os.getenv("PROMPTOPS_DB", "./promptops.db"))


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_conn()
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
            order_idx INTEGER DEFAULT 0
        );
        """
    )

    # Best-effort migrations for existing DBs
    for col, col_type in [
        ("run_id", "TEXT"),
        ("mlflow_uri", "TEXT"),
        ("regression", "INTEGER DEFAULT 0"),
    ]:
        try:
            col_name = col.split()[0]
            cur.execute(f"ALTER TABLE runs ADD COLUMN {col_name} {col_type.split()[0]}")
        except sqlite3.OperationalError:
            pass

    conn.commit()
    conn.close()


def insert_run(data: dict[str, Any]) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO runs (
            prompt_name, prompt_hash, model, run_id, mlflow_uri, judge_score, objective,
            prompt_tokens, completion_tokens, total_tokens, latency_ms, context_window_used,
            regression
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["prompt_name"],
            data["prompt_hash"],
            data["model"],
            data.get("run_id"),
            data.get("mlflow_uri"),
            data.get("judge_score"),
            data.get("objective"),
            data.get("prompt_tokens"),
            data.get("completion_tokens"),
            data.get("total_tokens"),
            data.get("latency_ms"),
            data.get("context_window_used"),
            1 if data.get("regression") else 0,
        ),
    )
    row_id = cur.lastrowid
    conn.commit()
    conn.close()
    return row_id


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
) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO run_results (
            run_id, test_idx, input, expected, output,
            judge_score, judge_criteria, judge_reasoning, metrics
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        ),
    )
    conn.commit()
    conn.close()


def get_run_results(run_id: int) -> list[dict[str, Any]]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM run_results WHERE run_id = ? ORDER BY test_idx",
        (run_id,),
    )
    rows = cur.fetchall()
    conn.close()
    results = []
    for row in rows:
        d = dict(row)
        d["input"] = json.loads(d["input"]) if d["input"] else {}
        d["metrics"] = json.loads(d["metrics"]) if d["metrics"] else {}
        d["judge_criteria"] = json.loads(d["judge_criteria"]) if d["judge_criteria"] else {}
        results.append(d)
    return results


def get_best_for_prompt(prompt_name: str) -> dict[str, Any] | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM runs WHERE prompt_name = ? ORDER BY objective DESC LIMIT 1",
        (prompt_name,),
    )
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def top_runs(limit: int = 10) -> list[dict[str, Any]]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM runs ORDER BY objective DESC LIMIT ?",
        (limit,),
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def recent_runs(limit: int = 50) -> list[dict[str, Any]]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM runs ORDER BY created_at DESC LIMIT ?",
        (limit,),
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_run(run_id: int) -> dict[str, Any] | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


# --- Suite CRUD ---

def list_suites() -> list[dict[str, Any]]:
    conn = get_conn()
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
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_suite(suite_id: int) -> dict[str, Any] | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM suites WHERE id = ?", (suite_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def create_suite(name: str, description: str | None = None) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO suites (name, description) VALUES (?, ?)",
        (name, description),
    )
    row_id = cur.lastrowid
    conn.commit()
    conn.close()
    return row_id


def delete_suite(suite_id: int) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM suites WHERE id = ?", (suite_id,))
    conn.commit()
    conn.close()


def get_suite_cases(suite_id: int) -> list[dict[str, Any]]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM suite_cases WHERE suite_id = ? ORDER BY order_idx, id",
        (suite_id,),
    )
    rows = cur.fetchall()
    conn.close()
    results = []
    for row in rows:
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
    order_idx: int = 0,
) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO suite_cases (suite_id, input, expected, rubric, order_idx) VALUES (?, ?, ?, ?, ?)",
        (
            suite_id,
            json.dumps(input_data),
            expected,
            json.dumps(rubric) if rubric else None,
            order_idx,
        ),
    )
    row_id = cur.lastrowid
    conn.commit()
    conn.close()
    return row_id


def remove_suite_case(case_id: int) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM suite_cases WHERE id = ?", (case_id,))
    conn.commit()
    conn.close()
