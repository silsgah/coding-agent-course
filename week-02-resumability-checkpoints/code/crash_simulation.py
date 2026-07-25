"""
Week 2 — Crash Simulation
==========================

Demonstrates:
1. Start a multi-step agent task
2. Simulate a crash mid-way (after N tool calls)
3. Resume from checkpoint
4. Show that no tool calls are repeated

Usage:
    python crash_simulation.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from shared.config import validate_setup
from shared.models import get_provider, Message
from shared.utils import print_header, console

from checkpoint import CheckpointWriter, CheckpointReader

# Reuse Week 1 tools
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "week-01-bare-agent-loop" / "code"))
from tools import TOOLS, TOOL_SCHEMAS, execute_tool


SYSTEM_PROMPT = """\
You are a coding assistant. Complete the following multi-step task thoroughly.
Use tools to accomplish each step before moving to the next.
"""

CRASH_AFTER_N_TOOLS = 2  # Simulate crash after this many tool calls


async def run_with_crash(session_dir: Path) -> None:
    """Run an agent task, simulating a crash after N tool calls."""
    provider = get_provider()
    writer = CheckpointWriter(session_dir)

    task = (
        "Please do these three things:\n"
        "1. List the files in the current directory\n"
        "2. Create a file called 'status.txt' with the text 'Agent was here'\n"
        "3. Read back the file to confirm it was written correctly"
    )

    console.print("\n[bold red]🔥 Phase 1: Running with simulated crash...[/bold red]")
    console.print(f"[dim]Will crash after {CRASH_AFTER_N_TOOLS} tool calls[/dim]\n")

    # Log the user message
    writer.log_user_message(task)
    history = [
        Message(role="system", content=SYSTEM_PROMPT),
        Message(role="user", content=task),
    ]

    tool_call_count = 0

    for iteration in range(10):
        response = await provider.chat(history, tools=TOOL_SCHEMAS)

        if response.tool_calls:
            for tc in response.tool_calls:
                tool_call_count += 1
                console.print(f"\n🔧 Tool call #{tool_call_count}: {tc.name}")

                # Log the tool call
                writer.log_tool_call(tc.name, tc.arguments, tc.id)

                # ── SIMULATE CRASH ──
                if tool_call_count >= CRASH_AFTER_N_TOOLS:
                    console.print("\n[bold red]💥 CRASH! Process killed mid-execution![/bold red]")
                    console.print("[dim]The tool call was logged but never executed.[/dim]")
                    console.print(f"[dim]Checkpoint saved to: {session_dir}/checkpoint.jsonl[/dim]\n")
                    return

                # Execute the tool
                result = execute_tool(tc.name, tc.arguments)
                writer.log_tool_result(tc.name, result, tc.id)
                writer.log_step_complete(tc.id)

                history.append(Message(role="assistant", content="", tool_calls=[{
                    "id": tc.id, "name": tc.name, "arguments": tc.arguments,
                }]))
                history.append(Message(role="tool", content=result, tool_call_id=tc.id))

            continue

        if response.content:
            writer.log_assistant_response(response.content)
            console.print(f"\n✅ Done: {response.content[:200]}")
            return


async def resume_from_checkpoint(session_dir: Path) -> None:
    """Resume a crashed run from its checkpoint."""
    console.print("\n[bold green]🔄 Phase 2: Resuming from checkpoint...[/bold green]\n")

    reader = CheckpointReader(session_dir)
    if not reader.has_checkpoint():
        console.print("[red]No checkpoint found![/red]")
        return

    state = reader.load()

    if state.is_complete:
        console.print("[green]Run was already complete — nothing to resume.[/green]")
        return

    # Rebuild the message history
    provider = get_provider()
    writer = CheckpointWriter(session_dir)

    history = [Message(role="system", content=SYSTEM_PROMPT)]
    for msg in state.messages:
        history.append(Message(
            role=msg["role"],
            content=msg.get("content", ""),
            tool_calls=msg.get("tool_calls", []),
            tool_call_id=msg.get("tool_call_id"),
        ))

    console.print(f"[cyan]Continuing from {len(state.messages)} messages...[/cyan]\n")

    # Continue the loop
    for iteration in range(10):
        response = await provider.chat(history, tools=TOOL_SCHEMAS)

        if response.tool_calls:
            for tc in response.tool_calls:
                console.print(f"\n🔧 Tool call (resumed): {tc.name}")

                # Execute — this time no crash
                result = execute_tool(tc.name, tc.arguments)
                writer.log_tool_call(tc.name, tc.arguments, tc.id)
                writer.log_tool_result(tc.name, result, tc.id)
                writer.log_step_complete(tc.id)

                history.append(Message(role="assistant", content="", tool_calls=[{
                    "id": tc.id, "name": tc.name, "arguments": tc.arguments,
                }]))
                history.append(Message(role="tool", content=result, tool_call_id=tc.id))
            continue

        if response.content:
            writer.log_assistant_response(response.content)
            console.print(f"\n[green]✅ Resumed and completed: {response.content[:200]}[/green]")
            return


async def main() -> None:
    print_header(
        "Week 2 — Crash Simulation",
        "Watch the agent crash and resume without repeating work",
    )
    validate_setup()

    session_dir = Path("sessions") / "crash-demo"

    # Clean up any previous run
    if session_dir.exists():
        import shutil
        shutil.rmtree(session_dir)

    # Phase 1: Run and crash
    await run_with_crash(session_dir)

    # Phase 2: Resume
    await resume_from_checkpoint(session_dir)

    # Show the checkpoint log
    console.print("\n[bold cyan]📋 Full checkpoint log:[/bold cyan]")
    log_path = session_dir / "checkpoint.jsonl"
    if log_path.exists():
        for i, line in enumerate(log_path.read_text().splitlines(), 1):
            import json
            event = json.loads(line)
            console.print(f"  [dim]{i}. {event['event_type']} ({event.get('step_id', 'n/a')})[/dim]")


if __name__ == "__main__":
    asyncio.run(main())
