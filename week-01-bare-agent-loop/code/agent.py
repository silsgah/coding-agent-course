"""
Week 1 — The Bare Agent Loop
=============================

Build one full user turn end-to-end:
    prompt → model → tool call → permission gate → execute → answer

This is the COMPLETE agent loop. Everything else in this course
is the harness that goes around it.

Usage:
    cd week-01-bare-agent-loop/code
    python agent.py

Inspired by the ReAct pattern from DecodingAI's coding agent course.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

# Add project root to path for shared imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from shared.config import validate_setup, DEFAULT_MODEL
from shared.models import get_provider, Message, ToolCall
from shared.utils import (
    print_header,
    print_step,
    print_tool_call,
    print_response,
    print_usage,
    console,
)

from tools import TOOLS, TOOL_SCHEMAS, execute_tool
from permission_gate import ask_permission


# ---------------------------------------------------------------------------
# System prompt — this is what steers the model
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """\
You are a helpful coding assistant. You can read files, write files, and run
shell commands to help the user with their coding tasks.

Rules:
1. Use tools to gather information before answering when possible.
2. Be concise and direct in your responses.
3. When writing code, explain what you're doing and why.
4. If a task might be destructive (deleting files, overwriting data), warn the
   user and confirm before proceeding.

Available tools: read_file, write_file, bash
"""


# ---------------------------------------------------------------------------
# The agent loop — this is it, the whole thing
# ---------------------------------------------------------------------------
async def agent_loop(user_message: str, history: list[Message]) -> str:
    """
    Run one complete agent turn.

    This is the ReAct loop:
        1. Send messages to the model
        2. If the model wants to call a tool:
           a. Ask permission (y/n)
           b. Execute the tool
           c. Add the result to history
           d. Go back to step 1
        3. If the model gives a text response: return it

    Args:
        user_message: What the user typed
        history: Conversation history (mutated in-place)

    Returns:
        The assistant's final text response
    """
    provider = get_provider()

    # Add the user message to history
    history.append(Message(role="user", content=user_message))

    # The loop — model calls tools until it's ready to answer
    max_iterations = 10  # Safety limit
    for iteration in range(max_iterations):
        print_step(iteration + 1, "Sending to model...")

        # Build the full message list (system + history)
        messages = [Message(role="system", content=SYSTEM_PROMPT)] + history

        # Call the model
        response = await provider.chat(messages, tools=TOOL_SCHEMAS)
        print_usage(response.usage)

        # Case 1: Model wants to call tools
        if response.tool_calls:
            for tool_call in response.tool_calls:
                print_tool_call(tool_call.name, tool_call.arguments)

                # ── THE PERMISSION GATE ──────────────────────────
                # This is the first harness component: nothing
                # executes without the human saying "yes".
                approved = ask_permission(tool_call.name, tool_call.arguments)

                if approved:
                    result = execute_tool(tool_call.name, tool_call.arguments)
                    console.print(f"[dim]✅ Tool result ({len(result)} chars)[/dim]")
                else:
                    result = "⛔ User denied this tool call."
                    console.print("[red]⛔ Denied by user[/red]")

                # Add the assistant's tool call and the tool result to history
                history.append(Message(
                    role="assistant",
                    content="",
                    tool_calls=[{
                        "id": tool_call.id,
                        "name": tool_call.name,
                        "arguments": tool_call.arguments,
                    }],
                    raw_parts=response.raw_parts,
                ))
                history.append(Message(
                    role="tool",
                    content=result,
                    tool_call_id=tool_call.id,
                ))

            # Loop back — model needs to see the tool results
            continue

        # Case 2: Model gave a text response — we're done
        if response.content:
            history.append(Message(role="assistant", content=response.content))
            return response.content

    return "⚠️ Agent reached maximum iterations without a final answer."


# ---------------------------------------------------------------------------
# Interactive REPL — the simplest possible interface
# ---------------------------------------------------------------------------
async def main() -> None:
    """Interactive agent REPL."""
    print_header(
        "Week 1 — The Bare Agent Loop",
        f"Model: {DEFAULT_MODEL} | Type 'quit' to exit",
    )
    validate_setup()

    history: list[Message] = []

    while True:
        try:
            user_input = console.input("\n[bold cyan]You:[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye![/dim]")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            console.print("[dim]Goodbye![/dim]")
            break

        response = await agent_loop(user_input, history)
        print_response(response)


if __name__ == "__main__":
    asyncio.run(main())
