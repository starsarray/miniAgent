from typing import Any
from uuid import uuid4

from ..tool_registry import Tool


def run(arguments: dict[str, Any], session: dict[str, Any]) -> dict[str, Any]:
    action = str(arguments.get("action", "")).strip().lower()
    tasks = session.setdefault("tasks", {})

    if action == "create":
        title = str(arguments.get("title", "")).strip()
        if not title:
            raise ValueError("title 不能为空")
        task_id = str(uuid4())[:8]
        task = {"id": task_id, "title": title, "status": "created"}
        tasks[task_id] = task
        session["last_task_id"] = task_id
        return {
            "tool": "todo",
            "success": True,
            "result": {"task": task, "answer": f"任务已创建：{title}，任务 ID：{task_id}，状态：created。"},
            "error": None,
        }

    if action == "list":
        task_list = list(tasks.values())
        if not task_list:
            answer = "当前没有待办任务。"
        else:
            answer = "当前待办任务：\n" + "\n".join(
                f"{task['id']}：{task['title']}，状态：{task['status']}" for task in task_list
            )
        return {"tool": "todo", "success": True, "result": {"tasks": task_list, "answer": answer}, "error": None}

    if action == "get":
        task_id = str(arguments.get("task_id") or session.get("last_task_id") or "").strip()
        if not task_id:
            raise ValueError("task_id 不能为空，且当前 session 没有 last_task_id")
        task = tasks.get(task_id)
        if not task:
            raise ValueError(f"任务不存在: {task_id}")
        return {
            "tool": "todo",
            "success": True,
            "result": {"task": task, "answer": f"任务进度：{task['title']}，当前状态：{task['status']}。"},
            "error": None,
        }

    if action == "update":
        task_id = str(arguments.get("task_id") or session.get("last_task_id") or "").strip()
        status = str(arguments.get("status", "")).strip()
        if not task_id or not status:
            raise ValueError("task_id 和 status 不能为空")
        task = tasks.get(task_id)
        if not task:
            raise ValueError(f"任务不存在: {task_id}")
        task["status"] = status
        return {
            "tool": "todo",
            "success": True,
            "result": {"task": task, "answer": f"任务已更新：{task['title']}，当前状态：{status}。"},
            "error": None,
        }

    raise ValueError("action 只支持 create/list/get/update")


def todo_tool() -> Tool:
    return Tool(
        name="todo",
        description="创建、查询、更新待办任务；用户说完成上个任务、完成刚才任务、更新任务状态时应调用 update。",
        parameters={
            "action": "string, required, create/list/get/update",
            "title": "string, create 时需要",
            "task_id": "string, get/update 可选；缺省使用 last_task_id",
            "status": "string, update 时需要；完成任务时使用 completed",
        },
        func=run,
    )
