from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = Path("./promptops.db")


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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    # Best-effort migrations for existing DBs
    for col, col_type in [
        ("run_id", "TEXT"),
        ("mlflow_uri", "TEXT"),
    ]:
        try:
            cur.execute(f"ALTER TABLE runs ADD COLUMN {col} {col_type}")
        except sqlite3.OperationalError:
            pass
    conn.commit()
    conn.close()


def insert_run(data: dict[str, Any]) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO runs (
            prompt_name, prompt_hash, model, run_id, mlflow_uri, judge_score, objective,
            prompt_tokens, completion_tokens, total_tokens, latency_ms, context_window_used
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        ),
    )
    conn.commit()
    conn.close()


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
