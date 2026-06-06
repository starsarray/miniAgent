import json
import os
import urllib.error
import urllib.request


class LLMClient:
    def __init__(self) -> None:
        provider = os.getenv("MINIAGENT_PROVIDER", "").lower()
        dashscope_key = os.getenv("DASHSCOPE_API_KEY")
        self.api_key = os.getenv("MINIAGENT_API_KEY") or dashscope_key or os.getenv("OPENAI_API_KEY")
        is_qwen = provider == "qwen" or bool(dashscope_key)
        default_base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1" if is_qwen else "https://api.openai.com/v1"
        default_model = "deepseek-v4-flash" if is_qwen else "qwen3.7-plus"
        self.base_url = os.getenv("MINIAGENT_BASE_URL", default_base_url).rstrip("/")
        self.model = os.getenv("MINIAGENT_MODEL", default_model)
        self.timeout = int(os.getenv("MINIAGENT_TIMEOUT", "60"))

    def chat(self, messages: list[dict[str, str]]) -> str:
        if not self.api_key:
            raise RuntimeError("未设置 MINIAGENT_API_KEY、DASHSCOPE_API_KEY 或 OPENAI_API_KEY")

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=data,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"LLM API HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"LLM API 请求失败: {exc.reason}") from exc

        try:
            return body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"LLM API 返回格式异常: {body}") from exc
