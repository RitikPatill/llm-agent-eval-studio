from pathlib import Path

import pytest
from pydantic import ValidationError

from agenteval.schema import TaskDefinition, load_task
from agenteval.tools import ToolExecutor

TASKS_DIR = Path(__file__).parent.parent / "tasks" / "sample"


def test_load_task_from_yaml():
    task = load_task(TASKS_DIR / "task_01_calculator.yaml")
    assert task.id == "calc_basic"
    assert "17" in task.prompt
    assert task.tools_available == ["calculator"]
    assert task.expected_tool_calls == ["calculator"]
    assert "102" in task.expected_output_keywords
    assert task.max_turns == 3


def test_task_defaults():
    task = TaskDefinition(
        id="t",
        prompt="p",
        tools_available=[],
        expected_tool_calls=[],
        expected_output_keywords=[],
    )
    assert task.max_turns == 5


def test_task_missing_required_field():
    with pytest.raises(ValidationError):
        TaskDefinition(
            id="t",
            tools_available=[],
            expected_tool_calls=[],
            expected_output_keywords=[],
        )


def test_calculator_valid():
    executor = ToolExecutor()
    result = executor.execute("calculator", {"expression": "17 * 6"})
    assert result.success is True
    assert result.output == "102"


def test_calculator_invalid():
    executor = ToolExecutor()
    result = executor.execute("calculator", {"expression": "import os"})
    assert result.success is False


def test_write_then_read_file():
    executor = ToolExecutor()
    write_result = executor.execute("write_file", {"path": "notes.txt", "content": "hello"})
    assert write_result.success is True
    read_result = executor.execute("read_file", {"path": "notes.txt"})
    assert read_result.success is True
    assert "hello" in read_result.output


def test_read_missing_file():
    executor = ToolExecutor()
    result = executor.execute("read_file", {"path": "does_not_exist.txt"})
    assert result.success is False


def test_web_search_stub():
    executor = ToolExecutor()
    result = executor.execute("web_search_stub", {"query": "pytest tutorial"})
    assert result.success is True
    assert "pytest tutorial" in result.output


def test_unknown_tool():
    executor = ToolExecutor()
    result = executor.execute("nonexistent_tool", {})
    assert result.success is False
