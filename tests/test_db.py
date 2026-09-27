from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path

import pytest

from agenteval.db import init_db, insert_run, insert_task_result, list_runs
from agenteval.runner import TaskResult


def _temp_db() -> str:
    f = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    f.close()
    return f.name


def _sample_run_kwargs(run_id: str = "run-abc") -> dict:
    return dict(
        run_id=run_id,
        provider="anthropic",
        model="claude-3-5-haiku-20241022",
        tasks_dir="tasks/sample",
        started_at="2024-01-01T00:00:00+00:00",
        total_tasks=2,
        passed_tasks=1,
        aggregate_score=0.75,
    )


def _sample_task_result(task_id: str = "calc_basic") -> TaskResult:
    return TaskResult(
        task_id=task_id,
        provider="anthropic",
        model="claude-3-5-haiku-20241022",
        passed=True,
        score=1.0,
        tool_calls_made=["calculator"],
        final_output="The answer is 42.",
        turns_used=2,
        score_breakdown={"tool_match": 1.0, "keyword": 1.0, "turn_penalty": 0.0},
    )


def test_init_db_creates_tables():
    db = _temp_db()
    conn = init_db(db)
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row["name"] for row in cursor.fetchall()}
    assert "runs" in tables
    assert "task_results" in tables
    conn.close()


def test_insert_and_list_run():
    db = _temp_db()
    conn = init_db(db)
    kwargs = _sample_run_kwargs()
    insert_run(conn, **kwargs)
    rows = list_runs(conn)
    assert len(rows) == 1
    row = rows[0]
    assert row["run_id"] == "run-abc"
    assert row["provider"] == "anthropic"
    assert row["passed_tasks"] == 1
    assert abs(row["aggregate_score"] - 0.75) < 1e-9
    conn.close()


def test_insert_task_result():
    db = _temp_db()
    conn = init_db(db)
    insert_run(conn, **_sample_run_kwargs("run-xyz"))
    result = _sample_task_result()
    insert_task_result(conn, "run-xyz", result)

    cursor = conn.execute("SELECT * FROM task_results WHERE run_id = 'run-xyz'")
    rows = cursor.fetchall()
    assert len(rows) == 1
    row = rows[0]
    assert row["task_id"] == "calc_basic"
    assert row["passed"] == 1
    assert json.loads(row["tool_calls_made"]) == ["calculator"]
    breakdown = json.loads(row["score_breakdown"])
    assert breakdown["tool_match"] == 1.0
    conn.close()


def test_list_runs_empty():
    db = _temp_db()
    conn = init_db(db)
    assert list_runs(conn) == []
    conn.close()
