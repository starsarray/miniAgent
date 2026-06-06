import argparse

from .agent import AgentRuntime
from .llm_client import LLMClient
from .memory import MemoryStore
from .tool_registry import ToolRegistry
from .tools.calculator import calculator_tool
from .tools.search import search_tool
from .tools.todo import todo_tool
from .tools.weather import weather_tool
from .trace_logger import TraceLogger


def build_agent(max_steps: int) -> AgentRuntime:
    memory = MemoryStore("data/sessions.json")
    logger = TraceLogger("logs/trace.log")
    registry = ToolRegistry()
    registry.register(calculator_tool())
    registry.register(search_tool())
    registry.register(todo_tool())
    registry.register(weather_tool())
    return AgentRuntime(
        llm_client=LLMClient(),
        memory=memory,
        tools=registry,
        logger=logger,
        max_steps=max_steps,
        verbose=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Minimal usable Agent")
    parser.add_argument("--session", default="default", help="Session id")
    parser.add_argument("--max-steps", type=int, default=10, help="Max agent loop steps")
    parser.add_argument("--once", help="Run one message and exit")
    parser.add_argument("--reset-session", action="store_true", help="Clear session memory before running")
    args = parser.parse_args()

    agent = build_agent(args.max_steps)
    if args.reset_session:
        agent.memory.delete_session(args.session)
        print(f"session reset: {args.session}")

    if args.once:
        print(agent.run(args.session, args.once))
        return

    tool_names = ", ".join(tool["name"] for tool in agent.tools.describe())
    print(f"miniAgent started. session={args.session}. tools={tool_names}. Type exit to quit.")
    while True:
        user_input = input("User> ").strip()
        if user_input.lower() in {"exit", "quit"}:
            break
        if not user_input:
            continue
        print(f"Agent> {agent.run(args.session, user_input)}")


if __name__ == "__main__":
    main()
