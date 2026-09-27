from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from agenteval.schema import TaskDefinition
from agenteval.scorers import (
    compute_score,
    score_keywords,
    score_tool_calls,
    score_turn_penalty,
)


# ---------------------------------------------------------------------------
# Scorer unit tests
# ---------------------------------------------------------------------------


def test_score_tool_calls_exact_match():
    assert score_tool_calls(["calculator"], ["calculator"]) == 1.0


def test_score_tool_calls_mismatch():
    assert score_tool_calls(["read_file", "calculator"], ["calculator", "read_file"]) == 0.0
    assert score_tool_calls(["calculator"], ["read_file"]) == 0.0
    assert score_tool_calls([], ["calculator"]) == 0.0


def test_score_keywords_all_present():
    assert score_keywords("The answer is 42 and it is correct", ["42", "correct"]) == 1.0


def test_score_keywords_partial():
    assert score_keywords("The answer is 42", ["42", "correct"]) == 0.5


def test_score_keywords_empty_list():
    assert score_keywords("anything", []) == 1.0


def test_turn_penalty_at_limit():
    assert score_turn_penalty(5, 5) == 0.1
    assert score_turn_penalty(6, 5) == 0.1  # over limit also penalised


def test_turn_penalty_under_limit():
    assert score_turn_penalty(3, 5) == 0.0
    assert score_turn_penalty(4, 5) == 0.0


def test_compute_score_perfect():
    task = TaskDefinition(
        id="t",
        prompt="p",
        tools_available=["calculator"],
        expected_tool_calls=["calculator"],
        expected_output_keywords=["42"],
        max_turns=5,
    )
    score, breakdown = compute_score(task, ["calculator"], "The answer is 42", 2)
    assert score == 1.0
    assert breakdown["tool_match"] == 1.0
    assert breakdown["keyword"] == 1.0
    assert breakdown["turn_penalty"] == 0.0


def test_compute_score_clamped_minimum():
    task = TaskDefinition(
        id="t",
        prompt="p",
        tools_available=["calculator"],
        expected_tool_calls=["calculator"],
        expected_output_keywords=["missing_keyword"],
        max_turns=5,
    )
    score, _ = compute_score(task, [], "", 5)
    assert score >= 0.0


# ---------------------------------------------------------------------------
# AgentRunner integration tests (mocked)
# ---------------------------------------------------------------------------


def _make_anthropic_task() -> TaskDefinition:
    return TaskDefinition(
        id="calc_test",
        prompt="Calculate 6 * 7.",
        tools_available=["calculator"],
        expected_tool_calls=["calculator"],
        expected_output_keywords=["42"],
        max_turns=5,
    )


def test_agentrunner_anthropic_mock():
    """Simulate: turn 1 → tool_use block, turn 2 → end_turn text block."""
    from agenteval.runner import AgentRunner

    # --- Build fake Anthropic responses ---
    # Turn 1: tool_use
    tool_use_block = SimpleNamespace(
        type="tool_use",
        id="tool_001",
        name="calculator",
        input={"expression": "6 * 7"},
    )
    turn1_response = SimpleNamespace(
        stop_reason="tool_use",
        content=[tool_use_block],
    )

    # Turn 2: end_turn with text
    text_block = SimpleNamespace(type="text", text="The answer is 42.")
    turn2_response = SimpleNamespace(
        stop_reason="end_turn",
        content=[text_block],
    )

    mock_client = MagicMock()
    mock_client.messages.create.side_effect = [turn1_response, turn2_response]

    with patch("agenteval.runner.anthropic.Anthropic", return_value=mock_client):
        runner = AgentRunner(provider="anthropic")
        result = runner.run(_make_anthropic_task())

    assert result.tool_calls_made == ["calculator"]
    assert result.turns_used == 2
    assert "42" in result.final_output
    assert result.score > 0
    assert result.passed is True


def test_agentrunner_openai_mock():
    """Simulate: turn 1 → tool call, turn 2 → final text."""
    from agenteval.runner import AgentRunner

    # Turn 1: tool call
    tc = SimpleNamespace(
        id="call_001",
        function=SimpleNamespace(
            name="calculator",
            arguments=json.dumps({"expression": "6 * 7"}),
        ),
    )
    turn1_message = SimpleNamespace(tool_calls=[tc], content=None)
    turn1_choice = SimpleNamespace(message=turn1_message)
    turn1_response = SimpleNamespace(choices=[turn1_choice])

    # Turn 2: final answer
    turn2_message = SimpleNamespace(tool_calls=None, content="The answer is 42.")
    turn2_choice = SimpleNamespace(message=turn2_message)
    turn2_response = SimpleNamespace(choices=[turn2_choice])

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [turn1_response, turn2_response]

    with patch("agenteval.runner.OpenAI", return_value=mock_client):
        runner = AgentRunner(provider="openai")
        result = runner.run(_make_anthropic_task())

    assert result.tool_calls_made == ["calculator"]
    assert result.turns_used == 2
    assert "42" in result.final_output
    assert result.score > 0
    assert result.passed is True
