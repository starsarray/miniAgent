from typing import Any

from ..tool_registry import Tool


MOCK_DOCS = [
    {
        "title": "miniAgent 架构",
        "content": "miniAgent 使用 Agent Runtime、Memory Store、LLM Client 和 Tool Registry。",
    },
    {
        "title": "工具调用流程",
        "content": "Agent 可以调用 calculator、search、todo 工具，并将结果写入 memory。",
    },
    {
        "title": "Memory 说明",
        "content": "收到用户输入后读取 memory，工具调用后和最终回复后写入 memory。",
    },
]


def run(arguments: dict[str, Any], session: dict[str, Any]) -> dict[str, Any]:
    query = str(arguments.get("query", "")).strip()
    if not query:
        raise ValueError("query 不能为空")

    keywords = [word.lower() for word in query.split()]
    results = []
    for doc in MOCK_DOCS:
        text = f"{doc['title']} {doc['content']}".lower()
        score = sum(1 for word in keywords if word in text)
        if score:
            results.append({"score": score, **doc})

    hit = bool(results)
    if not results:
        results = [{"score": 0, **MOCK_DOCS[0]}]

    results.sort(key=lambda item: item["score"], reverse=True)
    top_results = results[:3]
    lines = [f"{item['title']}：{item['content']}" for item in top_results]
    prefix = "搜索结果" if hit else "没有命中关键词，返回默认资料"
    return {
        "tool": "search",
        "success": True,
        "result": {"items": top_results, "answer": f"{prefix}：\n" + "\n".join(lines)},
        "error": None,
    }


def search_tool() -> Tool:
    return Tool(
        name="search",
        description="基于 mock 文档执行搜索，适合查询系统说明或示例资料。",
        parameters={"query": "string, required, 搜索关键词"},
        func=run,
    )
