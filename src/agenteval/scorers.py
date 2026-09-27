from __future__ import annotations

from agenteval.schema import TaskDefinition


def score_tool_calls(made: list[str], expected: list[str]) -> float:
    """1.0 if made == expected (exact order), 0.0 otherwise."""
    return 1.0 if made == expected else 0.0


def score_keywords(output: str, keywords: list[str]) -> float:
    """Fraction of keywords present (case-insensitive) in output. 1.0 if keywords is empty."""
    if not keywords:
        return 1.0
    lower = output.lower()
    matched = sum(1 for kw in keywords if kw.lower() in lower)
    return matched / len(keywords)


def score_turn_penalty(turns_used: int, max_turns: int) -> float:
    """0.1 deduction if turns_used >= max_turns, else 0.0."""
    return 0.1 if turns_used >= max_turns else 0.0


def compute_score(
    task: TaskDefinition,
    tool_calls_made: list[str],
    final_output: str,
    turns_used: int,
) -> tuple[float, dict[str, float]]:
    """
    Weighted composite: score = tool_match*0.5 + keyword*0.5 - turn_penalty
    Returns (score, breakdown_dict). Score clamped to [0.0, 1.0].
    passed = score >= 0.7
    """
    tool_match = score_tool_calls(tool_calls_made, task.expected_tool_calls)
    keyword = score_keywords(final_output, task.expected_output_keywords)
    turn_penalty = score_turn_penalty(turns_used, task.max_turns)

    score = tool_match * 0.5 + keyword * 0.5 - turn_penalty
    score = max(0.0, min(1.0, score))
    score = round(score, 4)

    breakdown = {
        "tool_match": round(tool_match, 4),
        "keyword": round(keyword, 4),
        "turn_penalty": round(turn_penalty, 4),
    }
    return score, breakdown
