from __future__ import annotations

import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agenteval.cli import build_parser, cmd_list, cmd_run
from agenteval.runner import TaskResult


def _fixed_result(task_id: str = "calc_basic") -> TaskResult:
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


@pytest.fixture()
def sample_yaml(tmp_path: Path) -> Path:
    task_file = tmp_path / "calc_basic.yaml"
    task_file.write_text(
        textwrap.dedent("""\
            id: calc_basic
            prompt: "What is 6 * 7?"
            tools_available: [calculator]
            expected_tool_calls: [calculator]
            expected_output_keywords: ["42"]
            max_turns: 3
        """)
    )
    return tmp_path


def test_cmd_run_prints_table(sample_yaml: Path, tmp_path: Path, capsys):
    db_path = str(tmp_path / "test.db")
    args = build_parser().parse_args(
        ["run", str(sample_yaml), "--provider", "anthropic", "--db", db_path]
    )

    with patch("agenteval.cli.AgentRunner") as MockRunner:
        instance = MockRunner.return_value
        instance.model = "claude-3-5-haiku-20241022"
        instance.run.return_value = _fixed_result()
        cmd_run(args)

    assert Path(db_path).exists()
    instance.run.assert_called_once()


def test_cmd_list_empty(tmp_path: Path, capsys):
    db_path = str(tmp_path / "empty.db")
    args = build_parser().parse_args(["list", "--db", db_path])
    # Should not raise
    cmd_list(args)


def test_build_parser_run_defaults():
    args = build_parser().parse_args(["run", "tasks/"])
    assert args.provider == "anthropic"
    assert args.model is None
    assert args.db == "agenteval.db"
    assert args.tasks_dir == "tasks/"


def test_build_parser_list():
    args = build_parser().parse_args(["list"])
    assert args.func.__name__ == "cmd_list"
