import ast
import operator
from typing import Any

from ..tool_registry import Tool


OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _eval(node: ast.AST) -> int | float:
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in OPS:
        return OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in OPS:
        return OPS[type(node.op)](_eval(node.operand))
    raise ValueError("只支持数字和基础四则运算")


def run(arguments: dict[str, Any], session: dict[str, Any]) -> dict[str, Any]:
    expression = str(arguments.get("expression", "")).strip()
    if not expression:
        raise ValueError("expression 不能为空")
    result = _eval(ast.parse(expression, mode="eval"))
    return {"tool": "calculator", "success": True, "result": result, "error": None}


def calculator_tool() -> Tool:
    return Tool(
        name="calculator",
        description="执行基础数学计算，支持 + - * / // % ** 和括号。",
        parameters={"expression": "string, required, 例如 '1 + 2 * 3'"},
        func=run,
    )
