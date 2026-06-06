# AI Prompt 与问题解决记录

## Prompt 目标

让 LLM 在 Agent Runtime 中只输出结构化 JSON，便于程序判断是直接回复还是调用工具。

## 核心 Prompt

```text
You are a minimal Agent runtime controller.
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
- Never output markdown outside the JSON object.
```

## 问题解决记录

1. 多轮对话：使用 `session_id` 关联 `messages`。
2. 跨轮次继续执行：使用 `todo` 工具保存 `tasks` 和 `last_task_id`。
3. 工具调用：LLM 输出 `tool_call` JSON，Runtime 通过 Tool Registry 执行。
4. 最大步数：Runtime 使用 `max_steps` 限制循环。
5. 异常处理：Runtime 捕获异常并返回可读错误。
6. Trace：执行过程写入 `data/sessions.json` 和 `logs/trace.log`。
7. API Key：通过环境变量读取，不硬编码。
8. 天气查询：新增 `weather` 工具，由 LLM 判断是否调用。
9. 记忆管理：Runtime 只保留最近 10 轮原文记忆；1 轮 = 用户一次输入 + 工具调用 + Agent 最终回答；超过 10 轮时，用 LLM 将 `已有 summary + 刚掉出最近 10 轮的一轮旧记忆` 增量压缩为 `summary`，最多 200 字。
10. 决策方式：工具选择、直接回复、任务完成均交给 LLM 判断，Runtime 不做关键词抢判。
