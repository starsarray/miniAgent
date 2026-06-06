import json
import re
from typing import Any


SYSTEM_PROMPT = """You are a minimal Agent runtime controller.
You must answer in JSON only.

Available action formats:
1. Final answer:
{"type":"final","answer":"..."}

2. Tool call:
{"type":"tool_call","tool":"tool_name","arguments":{...}}

Rules:
- Decide by yourself whether to answer directly, call a tool, or finish the task.
- Use tools when calculation, search, weather, document/task state, or task progress is needed.
- After receiving tool results, decide whether to call another tool or return final.
- If a tool result already satisfies the user request, return final.
- If user refers to previous context, use summary memory and recent memory.
- One round means one user input plus all tool calls and the final assistant answer for that input.
- Use explicit turn_no labels when answering questions about "第几轮".
- Do not print turn_no labels such as "[第2轮]" in final answers unless the user explicitly asks about rounds.
- Never output markdown outside the JSON object.
"""

SUMMARY_PROMPT = """You compress Agent memory incrementally.
You will receive:
1. Existing summary memory.
2. Old round memory that just fell out of the recent 10 rounds.

Return JSON only:
{"summary":"..."}

Rules:
- Keep summary within 200 Chinese characters or 200 ASCII characters.
- Preserve important user preferences, task ids/status, facts, tool results, and unresolved requests.
- Preserve turn numbers when useful for answering history questions.
- Merge existing summary and new old round memory into one concise summary.
"""

class AgentRuntime:
    RECENT_USER_ROUNDS = 10
    SUMMARY_MAX_CHARS = 200

    def __init__(self, llm_client, memory, tools, logger, max_steps: int = 10, verbose: bool = False):
        self.llm_client = llm_client
        self.memory = memory
        self.tools = tools
        self.logger = logger
        self.max_steps = max_steps
        self.verbose = verbose

    def run(self, session_id: str, user_input: str) -> str:
        try:
            turn_no = self.memory.increment_turn_count(session_id)
            self.memory.add_message(session_id, "user", user_input, turn_no=turn_no)
            self.logger.log({"session_id": session_id, "type": "user_input", "content": user_input})
            self._compact_memory(session_id)

            for step in range(1, self.max_steps + 1):
                session = self.memory.get_session(session_id)
                messages = self._build_messages(session)
                raw = self.llm_client.chat(messages)
                action = self._parse_action(raw)

                self._trace(session_id, step, "llm_decision", {"raw": raw}, action)

                if action.get("type") == "final":
                    answer = str(action.get("answer", "")).strip() or "没有生成有效回复。"
                    return self._finish(session_id, answer)

                if action.get("type") == "tool_call":
                    self._execute_tool_action(session_id, session, step, action)
                    continue

                raise ValueError(f"Unknown action type: {action.get('type')}")

            answer = "已达到最大执行步数，本次任务暂时停止。"
            self.logger.log({"session_id": session_id, "type": "max_steps", "max_steps": self.max_steps})
            return self._finish(session_id, answer)
        except Exception as exc:
            message = f"执行失败：{exc}"
            self.logger.log({"session_id": session_id, "type": "error", "error": str(exc)})
            return message

    def _build_messages(self, session: dict[str, Any]) -> list[dict[str, str]]:
        tool_descriptions = json.dumps(self.tools.describe(), ensure_ascii=False, indent=2)
        memory_state = {
            "session_id": session["session_id"],
            "tasks": session.get("tasks", {}),
            "last_task_id": session.get("last_task_id"),
            "last_answer": session.get("last_answer"),
            "completed_answer_count": session.get("answer_count", 0),
            "next_answer_number": int(session.get("answer_count", 0)) + 1,
            "completed_round_count": session.get("turn_count", 0),
            "current_turn_no": session.get("current_turn_no"),
        }
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": f"Available tools:\n{tool_descriptions}"},
            {"role": "system", "content": f"Summary memory:\n{session.get('summary') or '无'}"},
            {"role": "system", "content": f"Session state:\n{json.dumps(memory_state, ensure_ascii=False)}"},
            {
                "role": "system",
                "content": (
                    f"Recent memory JSON: last {self.RECENT_USER_ROUNDS} rounds only. "
                    "Use turn_no only for reasoning about history; do not copy turn_no labels into final answers.\n"
                    f"{json.dumps(self._recent_memory_items(session), ensure_ascii=False)}"
                ),
            },
        ]

        current_turn = session.get("current_turn_no")
        current_items = [item for item in session.get("messages", []) if item.get("turn_no") == current_turn]
        if current_items:
            user_items = [item for item in current_items if item.get("role") == "user"]
            tool_items = [item for item in current_items if item.get("role") == "tool"]
            if user_items:
                messages.append({"role": "user", "content": user_items[-1].get("content", "")})
            for item in tool_items:
                messages.append({"role": "user", "content": f"Tool result:\n{item.get('content', '')}"})
        return messages

    def _parse_action(self, raw: str) -> dict[str, Any]:
        text = raw.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        match = re.search(r"\{.*\}", text, flags=re.S)
        if not match:
            raise ValueError(f"LLM did not return JSON: {raw}")
        return json.loads(match.group(0))

    def _trace(self, session_id: str, step: int, event_type: str, input_data: Any, output_data: Any) -> None:
        item = {
            "step": step,
            "type": event_type,
            "input": input_data,
            "output": output_data,
            "error": None,
        }
        self.memory.add_trace(session_id, item)
        self.logger.log({"session_id": session_id, **item})

    def _execute_tool_action(
        self,
        session_id: str,
        session: dict[str, Any],
        step: int,
        action: dict[str, Any],
    ) -> None:
        tool_name = action.get("tool")
        arguments = action.get("arguments") or {}
        self._show_tool_start(tool_name, arguments)
        tool_result = self.tools.execute(tool_name, arguments, session)
        self._show_tool_result(tool_result)
        self.memory.update_session(session_id, session)
        self.memory.add_message(
            session_id,
            "tool",
            json.dumps(tool_result, ensure_ascii=False),
            turn_no=session.get("current_turn_no"),
        )
        self._trace(session_id, step, "tool_call", {"tool": tool_name, "arguments": arguments}, tool_result)

    def _finish(self, session_id: str, answer: str) -> str:
        session = self.memory.get_session(session_id)
        self.memory.add_message(session_id, "assistant", answer, turn_no=session.get("current_turn_no"))
        self.memory.set_last_answer(session_id, answer)
        answer_count = self.memory.increment_answer_count(session_id)
        self.logger.log({"session_id": session_id, "type": "final", "answer": answer, "answer_count": answer_count})
        self._compact_memory(session_id)
        return answer

    def _show_tool_start(self, tool_name: str | None, arguments: dict[str, Any]) -> None:
        if not self.verbose:
            return
        args = json.dumps(arguments, ensure_ascii=False)
        print(f"Agent> 正在调用工具：{tool_name}，参数：{args}", flush=True)

    def _show_tool_result(self, tool_result: dict[str, Any]) -> None:
        if not self.verbose:
            return
        status = "成功" if tool_result.get("success") else "失败"
        result = tool_result.get("result") if tool_result.get("success") else tool_result.get("error")
        text = json.dumps(result, ensure_ascii=False)
        if len(text) > 160:
            text = text[:157] + "..."
        print(f"Agent> 工具执行{status}：{tool_result.get('tool')}，结果：{text}", flush=True)

    def _compact_memory(self, session_id: str) -> None:
        session = self.memory.get_session(session_id)
        messages = session.get("messages", [])
        split_index = self._recent_start_index(messages)
        if split_index <= 0:
            return

        old_messages = messages[:split_index]
        session["messages"] = messages[split_index:]
        session["summary"] = self._summarize_old_memory(session.get("summary", ""), old_messages)
        self.memory.update_session(session_id, session)
        self.logger.log(
            {
                "session_id": session_id,
                "type": "memory_compact",
                "old_messages": len(old_messages),
                "recent_messages": len(session["messages"]),
            }
        )

    def _recent_start_index(self, messages: list[dict[str, Any]]) -> int:
        user_count = 0
        for index in range(len(messages) - 1, -1, -1):
            if messages[index].get("role") == "user":
                user_count += 1
                if user_count == self.RECENT_USER_ROUNDS:
                    return index
        return 0

    def _recent_memory_items(self, session: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            {
                "turn_no": item.get("turn_no"),
                "role": item.get("role"),
                "content": item.get("content"),
            }
            for item in session.get("messages", [])
        ]

    def _summarize_old_memory(self, existing_summary: str, old_messages: list[dict[str, Any]]) -> str:
        old_rounds = self._format_rounds_for_summary(old_messages)
        try:
            raw = self.llm_client.chat(
                [
                    {"role": "system", "content": SUMMARY_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            f"Existing summary memory:\n{existing_summary or '无'}\n\n"
                            f"New old round memory:\n{old_rounds}"
                        ),
                    },
                ]
            )
            data = self._parse_action(raw)
            summary = str(data.get("summary", "")).strip()
            if summary:
                return self._limit_summary(summary)
        except Exception as exc:
            self.logger.log({"type": "memory_compact_error", "error": str(exc)})

        fallback = f"{existing_summary}；{old_rounds}" if existing_summary else old_rounds
        return self._limit_summary(fallback)

    def _format_rounds_for_summary(self, old_messages: list[dict[str, Any]]) -> str:
        lines = []
        for turn_no, items in self._group_by_turn(old_messages):
            user_text = ""
            assistant_text = ""
            tools = []
            for item in items:
                role = item.get("role")
                content = str(item.get("content", ""))
                if role == "user" and not user_text:
                    user_text = content
                elif role == "assistant":
                    assistant_text = content
                elif role == "tool":
                    tools.append(self._tool_name_from_content(content))
            tool_text = f"；工具={','.join(name for name in tools if name)}" if tools else ""
            lines.append(
                f"第{turn_no}轮：用户={self._short(user_text)}{tool_text}；回答={self._short(assistant_text)}"
            )
        return "\n".join(line for line in lines if line)

    def _group_by_turn(self, messages: list[dict[str, Any]]) -> list[tuple[int | str, list[dict[str, Any]]]]:
        grouped: list[tuple[int | str, list[dict[str, Any]]]] = []
        index_by_turn: dict[int | str, int] = {}
        for item in messages:
            turn_no = item.get("turn_no") or "未知"
            if turn_no not in index_by_turn:
                index_by_turn[turn_no] = len(grouped)
                grouped.append((turn_no, []))
            grouped[index_by_turn[turn_no]][1].append(item)
        return grouped

    def _tool_name_from_content(self, content: str) -> str:
        try:
            data = json.loads(content)
            return str(data.get("tool") or "")
        except json.JSONDecodeError:
            return ""

    def _short(self, text: str, limit: int = 160) -> str:
        text = " ".join(text.split())
        if len(text) <= limit:
            return text
        return text[: limit - 3] + "..."

    def _limit_summary(self, summary: str) -> str:
        summary = "；".join(part.strip() for part in summary.splitlines() if part.strip())
        if len(summary) <= self.SUMMARY_MAX_CHARS:
            return summary
        return summary[-self.SUMMARY_MAX_CHARS :]
