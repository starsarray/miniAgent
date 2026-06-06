# miniAgent

从零实现的最小可用 Agent，支持多轮对话、session 维护、工具调用循环、最大步数、异常处理、trace 日志和真实 LLM API。

## 运行方式

使用 Miniconda 创建环境：

```powershell
conda env create -f environment.yml
conda activate miniagent
```

设置千问 Key。

cmd：

```bat
set "DASHSCOPE_API_KEY=你的千问 key"
```

PowerShell：

```powershell
$env:DASHSCOPE_API_KEY="你的千问 key"
```

可选配置：

cmd：

```bat
set "MINIAGENT_PROVIDER=qwen"
set "MINIAGENT_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1"
set "MINIAGENT_MODEL=qwen-plus"
```

PowerShell：

```powershell
$env:MINIAGENT_PROVIDER="qwen"
$env:MINIAGENT_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
$env:MINIAGENT_MODEL="qwen-plus"
```

启动交互：

```powershell
python -m src.main --session demo
```

默认最大执行步数是 10，可手动调整：

```powershell
python -m src.main --session demo --max-steps 15
```

清空某个 session 后启动：

```powershell
python -m src.main --session demo --reset-session
```

单次运行：

```powershell
python -m src.main --session demo --once "帮我计算 12 * 8 + 3"
```

## 系统设计

核心模块：

- `src/main.py`：命令行入口。
- `src/agent.py`：Agent Runtime，负责主循环。
- `src/llm_client.py`：真实 LLM API 调用。
- `src/memory.py`：session 和 memory 存储。
- `src/tool_registry.py`：工具注册与调用。
- `src/tools/`：具体工具。
- `src/trace_logger.py`：执行日志。

Agent 执行流程：

1. 接收用户输入。
2. 读取当前 session memory。
3. 组装系统 prompt、工具描述、历史消息和任务状态。
4. 调用 LLM 获取 JSON 决策。
5. 如果是 `final`，返回最终答案。
6. 如果是 `tool_call`，调用工具并写入工具结果。
7. 循环执行，直到最终回复或达到最大步数。

## 工具

当前包含 4 个工具：

- `calculator`：基础数学计算。
- `search`：mock 搜索。
- `todo`：创建、查询、更新任务，用于跨轮次继续执行。
- `weather`：查询城市当前天气。

示例问题：

```text
123456789/987654321=？
查询西安天气
帮我创建一个待办任务：查看北京天气
刚才那个任务现在怎么样了？
搜索一下 memory 的说明
```

## Memory 召回与放置

Memory 文件位置：

```text
data/sessions.json
```

如果该文件为空，会自动重建；如果 JSON 损坏，会备份为 `data/sessions.json.broken` 后重建。

读取时机：

- 收到用户输入后。
- 每次调用 LLM 前。
- 工具需要读取任务状态时。

写入时机：

- 用户输入后写入 `messages`。
- 工具调用后写入 `messages`、`tasks`、`trace`。
- 最终回复后写入 `messages` 和 `last_answer`。

保存内容：

- `session_id`
- `messages`
- `tasks`
- `trace`
- `last_answer`
- `answer_count`
- `summary`

记忆轮数：

- `data/sessions.json` 会保存当前 session 的摘要记忆和最近 10 轮原文记忆。
- Runtime 只保留最近 10 轮对话作为 `messages`。
- 1 轮 = 用户一次输入 + 这次输入触发的工具调用 + Agent 最终回答。
- 超过 10 轮时，会把 `已有 summary + 刚掉出最近 10 轮的一轮旧记忆` 发给 LLM，生成新的增量摘要。
- `summary` 每次压缩后最多 200 字。
- 每次调用 LLM 时，发送 `summary`、最近 10 轮记忆、当前 session 状态和工具列表；轮次只作为元数据，不要求模型在普通回答中输出。
- `tasks`、`last_task_id`、`last_answer`、`answer_count`、`next_answer_number`、`turn_count`、`current_turn_no` 会作为 session 状态单独放入 prompt。

## Trace 日志

日志文件位置：

```text
logs/trace.log
```

日志内容包括用户输入、LLM 决策、工具调用、工具结果、异常和最终回复。

## 跨轮次示例

第一轮：

```text
帮我创建一个待办任务：完成 miniAgent 笔试题
```

第二轮：

```text
刚才那个任务现在怎么样了？
```

Agent 会通过同一个 `session_id` 读取 `tasks` 和 `last_task_id`，继续处理已有任务。

## 注意事项

- 不使用 LangChain、OpenHands 等 Agent 框架实现主流程。
- API Key 只从环境变量读取，不写入代码。
- 千问/DashScope 使用 OpenAI-compatible 接口，默认模型为 `qwen-plus`。
- 未设置 Key 时，程序会提示 `未设置 MINIAGENT_API_KEY、DASHSCOPE_API_KEY 或 OPENAI_API_KEY`。
