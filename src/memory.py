import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class MemoryStore:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({"sessions": {}})

    def get_session(self, session_id: str) -> dict[str, Any]:
        data = self._read()
        sessions = data.setdefault("sessions", {})
        if session_id not in sessions:
            sessions[session_id] = {
                "session_id": session_id,
                "messages": [],
                "summary": "",
                "tasks": {},
                "trace": [],
                "last_answer": None,
                "answer_count": 0,
                "turn_count": 0,
                "current_turn_no": 0,
            }
            self._write(data)
        if self._normalize_session(sessions[session_id]):
            self._write(data)
        return sessions[session_id]

    def update_session(self, session_id: str, session: dict[str, Any]) -> None:
        data = self._read()
        data.setdefault("sessions", {})[session_id] = session
        self._write(data)

    def delete_session(self, session_id: str) -> None:
        data = self._read()
        data.setdefault("sessions", {}).pop(session_id, None)
        self._write(data)

    def add_message(self, session_id: str, role: str, content: str, turn_no: int | None = None) -> None:
        session = self.get_session(session_id)
        if turn_no is None:
            turn_no = session.get("current_turn_no")
        message = {"role": role, "content": content, "created_at": self._now()}
        if turn_no:
            message["turn_no"] = turn_no
        session.setdefault("messages", []).append(message)
        self.update_session(session_id, session)

    def add_trace(self, session_id: str, item: dict[str, Any]) -> None:
        session = self.get_session(session_id)
        item = {"created_at": self._now(), **item}
        session.setdefault("trace", []).append(item)
        self.update_session(session_id, session)

    def set_last_answer(self, session_id: str, answer: str) -> None:
        session = self.get_session(session_id)
        session["last_answer"] = answer
        self.update_session(session_id, session)

    def increment_answer_count(self, session_id: str) -> int:
        session = self.get_session(session_id)
        session["answer_count"] = int(session.get("answer_count", 0)) + 1
        self.update_session(session_id, session)
        return session["answer_count"]

    def increment_turn_count(self, session_id: str) -> int:
        session = self.get_session(session_id)
        session["turn_count"] = int(session.get("turn_count", 0)) + 1
        session["current_turn_no"] = session["turn_count"]
        self.update_session(session_id, session)
        return session["turn_count"]

    def _read(self) -> dict[str, Any]:
        text = self.path.read_text(encoding="utf-8").strip()
        if not text:
            data = {"sessions": {}}
            self._write(data)
            return data
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = {"sessions": {}}
            backup = self.path.with_suffix(self.path.suffix + ".broken")
            self.path.replace(backup)
            self._write(data)
            return data
        if not isinstance(data, dict):
            data = {"sessions": {}}
            self._write(data)
        data.setdefault("sessions", {})
        return data

    def _write(self, data: dict[str, Any]) -> None:
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _normalize_session(self, session: dict[str, Any]) -> bool:
        changed = False
        had_answer_count = "answer_count" in session
        defaults = {
            "messages": [],
            "summary": "",
            "tasks": {},
            "trace": [],
            "last_answer": None,
            "answer_count": 0,
            "turn_count": 0,
            "current_turn_no": 0,
        }
        for key, value in defaults.items():
            if key not in session:
                session[key] = value
                changed = True

        turn_no = 0
        for message in session.get("messages", []):
            if message.get("role") == "user":
                turn_no += 1
            if turn_no and not message.get("turn_no"):
                message["turn_no"] = turn_no
                changed = True

        if turn_no > int(session.get("turn_count", 0)):
            session["turn_count"] = turn_no
            session["current_turn_no"] = turn_no
            changed = True

        if not had_answer_count:
            session["answer_count"] = sum(1 for item in session.get("messages", []) if item.get("role") == "assistant")
            changed = True

        return changed
