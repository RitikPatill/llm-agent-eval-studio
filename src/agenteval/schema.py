from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel


class ToolCallSpec(BaseModel):
    name: str
    arguments: dict[str, Any] = {}


class TaskDefinition(BaseModel):
    id: str
    prompt: str
    tools_available: list[str]
    expected_tool_calls: list[str]
    expected_output_keywords: list[str]
    max_turns: int = 5


def load_task(path: str | Path) -> TaskDefinition:
    """Load and validate a single YAML file → TaskDefinition."""
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return TaskDefinition(**data)
