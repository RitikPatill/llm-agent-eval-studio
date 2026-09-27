from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agenteval.db import init_db, insert_run, insert_task_result
from agenteval.runner import TaskResult
from agenteval.server import create_app


@pytest.fixture()
def db_path(tmp_path: Path) -> str:
    path = str(tmp_path / "test.db")
    return path


@pytest.fixture()
def populated_db(db_path: str) -> tuple[str, str]:
    """Returns (db_path, run_id) after inserting one run + two task results."""
    conn = init_db(db_path)
    run_id = "aaaabbbb-cccc-dddd-eeee-ffffffffffff"
    insert_run(
        conn,
        run_id=run_id,
        provider="anthropic",
        model="claude-haiku-4-5-20251001",
        tasks_dir="tasks/sample",
        started_at="2026-09-27T10:00:00+00:00",
        total_tasks=2,
        passed_tasks=1,
        aggregate_score=0.75,
    )
    for task_id, passed in [("calc_basic", True), ("web_search", False)]:
        insert_task_result(
            conn,
            run_id,
            TaskResult(
                task_id=task_id,
                provider="anthropic",
                model="claude-haiku-4-5-20251001",
                passed=passed,
                score=1.0 if passed else 0.5,
                tool_calls_made=["calculator"] if passed else [],
                final_output="The answer is 102" if passed else "Not found",
                turns_used=1,
                score_breakdown={"tool_match": 1.0, "keyword": 1.0, "turn_penalty": 0.0}
                if passed
                else {"tool_match": 0.0, "keyword": 1.0, "turn_penalty": 0.0},
            ),
        )
    conn.close()
    return db_path, run_id


def test_index_empty(db_path: str) -> None:
    conn = init_db(db_path)
    conn.close()
    client = TestClient(create_app(db_path=db_path))
    resp = client.get("/")
    assert resp.status_code == 200
    assert "No runs yet" in resp.text


def test_index_with_run(populated_db: tuple[str, str]) -> None:
    db_path, run_id = populated_db
    client = TestClient(create_app(db_path=db_path))
    resp = client.get("/")
    assert resp.status_code == 200
    assert run_id[:8] in resp.text


def test_run_detail_found(populated_db: tuple[str, str]) -> None:
    db_path, run_id = populated_db
    client = TestClient(create_app(db_path=db_path))
    resp = client.get(f"/run/{run_id}")
    assert resp.status_code == 200
    assert "calc_basic" in resp.text


def test_run_detail_not_found(db_path: str) -> None:
    conn = init_db(db_path)
    conn.close()
    client = TestClient(create_app(db_path=db_path))
    resp = client.get("/run/nonexistent")
    assert resp.status_code == 404
