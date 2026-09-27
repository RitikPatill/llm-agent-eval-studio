from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ToolResult(BaseModel):
    tool_name: str
    success: bool
    output: str


class ToolExecutor:
    def __init__(self) -> None:
        # Instance-level virtual filesystem — never share across test cases.
        self._fs: dict[str, str] = {}

    def execute(self, tool_name: str, arguments: dict[str, Any]) -> ToolResult:
        """Dispatch to _tool_<name>. Unknown tool → success=False."""
        handler = getattr(self, f"_tool_{tool_name}", None)
        if handler is None:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                output=f"Unknown tool: {tool_name}",
            )
        return handler(**arguments)

    # ------------------------------------------------------------------
    # Mock tool implementations
    # ------------------------------------------------------------------

    def _tool_read_file(self, path: str) -> ToolResult:
        if path in self._fs:
            return ToolResult(tool_name="read_file", success=True, output=self._fs[path])
        return ToolResult(tool_name="read_file", success=False, output="File not found")

    def _tool_write_file(self, path: str, content: str) -> ToolResult:
        self._fs[path] = content
        return ToolResult(tool_name="write_file", success=True, output=f"Written to {path}")

    def _tool_calculator(self, expression: str) -> ToolResult:
        # NOTE: eval with empty builtins blocks most attacks for a local dev
        # tool, but is NOT production-safe (e.g. ().__class__.__bases__ still
        # works). Do not use this in an untrusted environment.
        try:
            result = eval(expression, {"__builtins__": {}}, {})  # noqa: S307
            return ToolResult(tool_name="calculator", success=True, output=str(result))
        except Exception as exc:
            return ToolResult(tool_name="calculator", success=False, output=str(exc))

    def _tool_web_search_stub(self, query: str) -> ToolResult:
        return ToolResult(
            tool_name="web_search_stub",
            success=True,
            output=f"[stub] top result for: {query}",
        )
