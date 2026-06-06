from dataclasses import dataclass
from typing import Any, Callable


ToolFunc = Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    func: ToolFunc


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def describe(self) -> list[dict[str, Any]]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            }
            for tool in self._tools.values()
        ]

    def execute(self, name: str | None, arguments: dict[str, Any], session: dict[str, Any]) -> dict[str, Any]:
        if not name:
            return {"tool": None, "success": False, "result": None, "error": "工具名称不能为空"}
        tool = self._tools.get(name)
        if not tool:
            return {"tool": name, "success": False, "result": None, "error": f"工具不存在: {name}"}
        try:
            return tool.func(arguments, session)
        except Exception as exc:
            return {"tool": name, "success": False, "result": None, "error": str(exc)}
