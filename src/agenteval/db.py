from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from agenteval.runner import TaskResult

_DDL = """
CREATE TABLE IF NOT EXISTS runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          TEXT UNIQUE NOT NULL,
    provider        TEXT NOT NULL,
    model           TEXT NOT NULL,
    tasks_dir       TEXT NOT NULL,
    started_at      TEXT NOT NULL,
    total_tasks     INTEGER NOT NULL,
    passed_tasks    INTEGER NOT NULL,
    aggregate_score REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS task_results (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          TEXT NOT NULL,
    task_id         TEXT NOT NULL,
    passed          INTEGER NOT NULL,
    score           REAL NOT NULL,
    tool_calls_made TEXT NOT NULL,
    final_output    TEXT NOT NULL,
    turns_used      INTEGER NOT NULL,
    score_breakdown TEXT NOT NULL
);
"""


def init_db(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.executescript(_DDL)
    conn.commit()
    return conn


def insert_run(
    conn: sqlite3.Connection,
    run_id: str,
    provider: str,
    model: str,
    tasks_dir: str,
    started_at: str,
    total_tasks: int,
    passed_tasks: int,
    aggregate_score: float,
) -> None:
    conn.execute(
        """
        INSERT INTO runs (run_id, provider, model, tasks_dir, started_at,
                          total_tasks, passed_tasks, aggregate_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (run_id, provider, model, tasks_dir, started_at,
         total_tasks, passed_tasks, aggregate_score),
    )
    conn.commit()


def insert_task_result(conn: sqlite3.Connection, run_id: str, result: TaskResult) -> None:
    conn.execute(
        """
        INSERT INTO task_results (run_id, task_id, passed, score,
                                  tool_calls_made, final_output, turns_used, score_breakdown)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            result.task_id,
            int(result.passed),
            result.score,
            json.dumps(result.tool_calls_made),
            result.final_output,
            result.turns_used,
            json.dumps(result.score_breakdown),
        ),
    )
    conn.commit()


def list_runs(conn: sqlite3.Connection) -> list[dict]:
    cursor = conn.execute("SELECT * FROM runs ORDER BY started_at DESC")
    return [dict(row) for row in cursor.fetchall()]
