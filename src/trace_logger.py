import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class TraceLogger:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, item: dict[str, Any]) -> None:
        row = {"created_at": datetime.now(timezone.utc).isoformat(), **item}
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")
