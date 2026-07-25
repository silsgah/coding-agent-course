"""
Week 2 — Durable Runtime
=========================

Wraps the Week 1 agent loop with checkpoint write-through.
Every tool call result is persisted before the loop continues.

This is the durable version of agent.py — same loop, but crash-safe.

Usage:
    python durable_runtime.py
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from shared.config import validate_setup, DEFAULT_MODEL
from shared.models import get_provider, Message
from shared.utils import (
    print_header, print_tool_call, print_response, print_usage, console,
)

from checkpoint import CheckpointWriter, CheckpointReader

# Reuse Week 1 tools and permission gate
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "week-01-bare-agent-loop" / "code"))
from tools import TOOLS, TOOL_SCHEMAS, execute_tool
from permission_gate import ask_permission


SYSTEM_PROMPT = """\
You are a helpful coding assistant. You can read files, write files, and run
shell commands to help the user with their coding tasks.
"""


async def durable_agent_loop(
    user_message: str,
    history: list[Message],
    writer: CheckpointWriter,
) -> str:
    """
    The Week 1 agent loop, now with checkpoint write-through.

    Every tool call and result is persisted to disk before continuing.
    If the process crashes, we can resume from the checkpoint.
    """
    provider = get_provider()

    history.append(Message(role="user", content=user_message))
    writer.log_user_message(user_message)

    max_iterations = 10
    for iteration in range(max_iterations):
        messages = [Message(role="system", content=SYSTEM_PROMPT)] + history
        response = await provider.chat(messages, tools=TOOL_SCHEMAS)
        print_usage(response.usage)

        if response.tool_calls:
            for tool_call in response.tool_calls:
                step_id = uuid.uuid4().hex[:8]
                print_tool_call(tool_call.name, tool_call.arguments)

                # Log the intent BEFORE asking permission
                writer.log_tool_call(tool_call.name, tool_call.arguments, step_id)

                approved = ask_permission(tool_call.name, tool_call.arguments)

                if approved:
                    result = execute_tool(tool_call.name, tool_call.arguments)
                    # Log the result IMMEDIATELY after execution
                    writer.log_tool_result(tool_call.name, result, step_id)
                    writer.log_step_complete(step_id)
                else:
                    result = "⛔ User denied this tool call."
                    writer.log_tool_result(tool_call.name, result, step_id)

                history.append(Message(
                    role="assistant", content="",
                    tool_calls=[{"id": step_id, "name": tool_call.name, "arguments": tool_call.arguments}],
                ))
                history.append(Message(role="tool", content=result, tool_call_id=step_id))

            continue

        if response.content:
            history.append(Message(role="assistant", content=response.content))
            writer.log_assistant_response(response.content)
            return response.content

    return "⚠️ Agent reached maximum iterations."


async def main() -> None:
    print_header(
        "Week 2 — Durable Agent Runtime",
        f"Model: {DEFAULT_MODEL} | Checkpoints enabled | Type 'quit' to exit",
    )
    validate_setup()

    session_dir = Path("sessions") / "interactive"
    writer = CheckpointWriter(session_dir)
    reader = CheckpointReader(session_dir)

    # Try to resume from existing checkpoint
    history: list[Message] = []
    if reader.has_checkpoint():
        state = reader.load()
        if not state.is_complete:
            console.print("[yellow]Found incomplete session — resuming...[/yellow]")
            for msg in state.messages:
                history.append(Message(
                    role=msg["role"],
                    content=msg.get("content", ""),
                    tool_calls=msg.get("tool_calls", []),
                    tool_call_id=msg.get("tool_call_id"),
                ))
        else:
            console.print("[dim]Previous session was complete. Starting fresh.[/dim]")

    while True:
        try:
            user_input = console.input("\n[bold cyan]You:[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Session checkpointed. Goodbye![/dim]")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            console.print("[dim]Session checkpointed. Goodbye![/dim]")
            break

        response = await durable_agent_loop(user_input, history, writer)
        print_response(response)


if __name__ == "__main__":
    asyncio.run(main())
