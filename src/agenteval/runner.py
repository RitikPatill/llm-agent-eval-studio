from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

import anthropic
from openai import OpenAI

from agenteval.schema import TaskDefinition
from agenteval.scorers import compute_score
from agenteval.tools import ToolExecutor

TOOL_SCHEMAS: dict[str, dict] = {
    "calculator": {
        "description": "Evaluate a math expression and return the result.",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "A Python-evaluable math expression",
                }
            },
            "required": ["expression"],
        },
    },
    "read_file": {
        "description": "Read the contents of a file from the virtual filesystem.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path of the file to read",
                }
            },
            "required": ["path"],
        },
    },
    "write_file": {
        "description": "Write content to a file in the virtual filesystem.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path of the file to write",
                },
                "content": {
                    "type": "string",
                    "description": "The content to write to the file",
                },
            },
            "required": ["path", "content"],
        },
    },
    "web_search_stub": {
        "description": "Search the web and return a stub top result.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query",
                }
            },
            "required": ["query"],
        },
    },
}


@dataclass
class TaskResult:
    task_id: str
    provider: str
    model: str
    passed: bool
    score: float
    tool_calls_made: list[str] = field(default_factory=list)
    final_output: str = ""
    turns_used: int = 0
    score_breakdown: dict[str, float] = field(default_factory=dict)


class AgentRunner:
    def __init__(self, provider: str = "anthropic", model: str | None = None) -> None:
        self.provider = provider
        if provider == "anthropic":
            self.model = model or os.environ.get(
                "ANTHROPIC_MODEL", "claude-3-5-haiku-20241022"
            )
        else:
            self.model = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    def run(self, task: TaskDefinition) -> TaskResult:
        """Entry point — dispatches to _run_anthropic or _run_openai."""
        executor = ToolExecutor()
        if self.provider == "anthropic":
            tool_calls_made, final_output, turns_used = self._run_anthropic(
                task, executor
            )
        else:
            tool_calls_made, final_output, turns_used = self._run_openai(
                task, executor
            )

        score, breakdown = compute_score(task, tool_calls_made, final_output, turns_used)
        passed = score >= 0.7

        return TaskResult(
            task_id=task.id,
            provider=self.provider,
            model=self.model,
            passed=passed,
            score=score,
            tool_calls_made=tool_calls_made,
            final_output=final_output,
            turns_used=turns_used,
            score_breakdown=breakdown,
        )

    def _run_anthropic(
        self, task: TaskDefinition, executor: ToolExecutor
    ) -> tuple[list[str], str, int]:
        """Returns (tool_calls_made, final_output, turns_used)."""
        client = anthropic.Anthropic()
        tools = self._anthropic_tools(task.tools_available)
        messages: list[dict] = [{"role": "user", "content": task.prompt}]
        tool_calls_made: list[str] = []
        final_output = ""

        for turn in range(task.max_turns):
            response = client.messages.create(
                model=self.model,
                tools=tools,
                messages=messages,
                max_tokens=1024,
            )

            if response.stop_reason == "end_turn":
                for block in response.content:
                    if hasattr(block, "text"):
                        final_output = block.text
                        break
                return tool_calls_made, final_output, turn + 1

            # Collect tool_use blocks and execute them
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_calls_made.append(block.name)
                    result = executor.execute(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result.output,
                    })

            # Append assistant turn verbatim + tool results
            messages.append({"role": "assistant", "content": response.content})
            if tool_results:
                messages.append({"role": "user", "content": tool_results})

        return tool_calls_made, final_output, task.max_turns

    def _run_openai(
        self, task: TaskDefinition, executor: ToolExecutor
    ) -> tuple[list[str], str, int]:
        """Returns (tool_calls_made, final_output, turns_used)."""
        client = OpenAI()
        tools = self._openai_tools(task.tools_available)
        messages: list[dict] = [{"role": "user", "content": task.prompt}]
        tool_calls_made: list[str] = []
        final_output = ""

        for turn in range(task.max_turns):
            response = client.chat.completions.create(
                model=self.model,
                tools=tools,
                messages=messages,
            )
            message = response.choices[0].message

            if message.tool_calls is None:
                final_output = message.content or ""
                return tool_calls_made, final_output, turn + 1

            # Append assistant message (tool_calls present, content may be None)
            messages.append(
                {
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": message.tool_calls,
                }
            )

            for tc in message.tool_calls:
                tool_calls_made.append(tc.function.name)
                args = json.loads(tc.function.arguments)
                result = executor.execute(tc.function.name, args)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result.output,
                    }
                )

        return tool_calls_made, final_output, task.max_turns

    def _anthropic_tools(self, tool_names: list[str]) -> list[dict]:
        """Build Anthropic tools list from TOOL_SCHEMAS for the given names."""
        result = []
        for name in tool_names:
            if name not in TOOL_SCHEMAS:
                print(f"Warning: unknown tool '{name}' — skipping")
                continue
            schema = TOOL_SCHEMAS[name]
            result.append(
                {
                    "name": name,
                    "description": schema["description"],
                    "input_schema": schema["input_schema"],
                }
            )
        return result

    def _openai_tools(self, tool_names: list[str]) -> list[dict]:
        """Build OpenAI tools list (wraps each schema in {"type":"function","function":{...}})."""
        result = []
        for name in tool_names:
            if name not in TOOL_SCHEMAS:
                print(f"Warning: unknown tool '{name}' — skipping")
                continue
            schema = TOOL_SCHEMAS[name]
            # Convert input_schema to OpenAI's parameters format
            result.append(
                {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": schema["description"],
                        "parameters": schema["input_schema"],
                    },
                }
            )
        return result
