"""
Week 3 — Replay Harness
========================

Fork a run from any checkpoint step and continue with
the same or a different model.

Usage:
    python replay_harness.py --task "your task here"
    python replay_harness.py --replay sessions/run-id --from-step 3
    python replay_harness.py --replay sessions/run-id --from-step 3 --model gemini-2.5-pro
"""

from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import sys
import uuid
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from shared.config import validate_setup, DEFAULT_MODEL
from shared.models import get_provider, Message
from shared.utils import print_header, print_tool_call, print_response, print_usage, console

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "week-02-resumability-checkpoints" / "code"))
from checkpoint import CheckpointWriter, CheckpointReader

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "week-01-bare-agent-loop" / "code"))
from tools import TOOL_SCHEMAS, execute_tool


SYSTEM_PROMPT = """\
You are a helpful coding assistant. You can read files, write files, and run
shell commands to help the user with their coding tasks.
"""


def load_checkpoint_events(session_dir: Path) -> list[dict]:
    """Load raw events from a checkpoint file."""
    log_path = session_dir / "checkpoint.jsonl"
    events = []
    if log_path.exists():
        with open(log_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
    return events


def rebuild_history_to_step(events: list[dict], max_step: int | None = None) -> list[Message]:
    """Rebuild conversation history from checkpoint events, stopping at max_step."""
    history = []
    step_count = 0

    for event in events:
        event_type = event["event_type"]
        data = event["data"]

        if event_type == "user_message":
            history.append(Message(role="user", content=data["message"]))

        elif event_type == "tool_call":
            history.append(Message(
                role="assistant", content="",
                tool_calls=[{
                    "id": event.get("step_id", ""),
                    "name": data["tool_name"],
                    "arguments": data["arguments"],
                }],
            ))

        elif event_type == "tool_result":
            history.append(Message(
                role="tool",
                content=data["result"],
                tool_call_id=event.get("step_id", ""),
            ))

        elif event_type == "step_complete":
            step_count += 1
            if max_step is not None and step_count >= max_step:
                console.print(f"[cyan]⏸️  Stopped replay at step {step_count}[/cyan]")
                break

        elif event_type == "assistant_response":
            history.append(Message(role="assistant", content=data["response"]))

    return history


async def run_fresh(task: str, session_dir: Path, model: str | None = None) -> None:
    """Run a fresh task (creates a new session)."""
    provider = get_provider(model=model)
    writer = CheckpointWriter(session_dir)

    console.print(f"\n[bold]🚀 New run | Model: {provider} | Session: {session_dir.name}[/bold]\n")

    writer.log_user_message(task)
    history = [
        Message(role="system", content=SYSTEM_PROMPT),
        Message(role="user", content=task),
    ]

    for iteration in range(10):
        response = await provider.chat(history, tools=TOOL_SCHEMAS)
        print_usage(response.usage)

        if response.tool_calls:
            for tc in response.tool_calls:
                print_tool_call(tc.name, tc.arguments)
                step_id = uuid.uuid4().hex[:8]
                writer.log_tool_call(tc.name, tc.arguments, step_id)

                result = execute_tool(tc.name, tc.arguments)
                writer.log_tool_result(tc.name, result, step_id)
                writer.log_step_complete(step_id)

                history.append(Message(role="assistant", content="", tool_calls=[{
                    "id": step_id, "name": tc.name, "arguments": tc.arguments,
                }]))
                history.append(Message(role="tool", content=result, tool_call_id=step_id))
            continue

        if response.content:
            writer.log_assistant_response(response.content)
            print_response(response.content)
            return


async def replay_from(
    source_dir: Path,
    from_step: int,
    target_dir: Path,
    model: str | None = None,
) -> None:
    """Replay a run from a specific step, optionally with a different model."""
    events = load_checkpoint_events(source_dir)
    if not events:
        console.print("[red]No events found in source session![/red]")
        return

    console.print(f"\n[bold]🔄 Replay | From step {from_step} | "
                  f"Source: {source_dir.name} | Model: {model or DEFAULT_MODEL}[/bold]\n")

    # Rebuild history up to the fork point
    history = rebuild_history_to_step(events, max_step=from_step)
    history.insert(0, Message(role="system", content=SYSTEM_PROMPT))

    # Continue with (potentially different) model
    provider = get_provider(model=model)
    writer = CheckpointWriter(target_dir)

    # Log the replay metadata
    writer.write(type("Event", (), {
        "event_type": "replay_metadata",
        "data": {
            "source_session": str(source_dir),
            "from_step": from_step,
            "model": model or DEFAULT_MODEL,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "step_id": "replay",
    })())

    for iteration in range(10):
        response = await provider.chat(history, tools=TOOL_SCHEMAS)
        print_usage(response.usage)

        if response.tool_calls:
            for tc in response.tool_calls:
                print_tool_call(tc.name, tc.arguments)
                step_id = uuid.uuid4().hex[:8]
                writer.log_tool_call(tc.name, tc.arguments, step_id)

                result = execute_tool(tc.name, tc.arguments)
                writer.log_tool_result(tc.name, result, step_id)
                writer.log_step_complete(step_id)

                history.append(Message(role="assistant", content="", tool_calls=[{
                    "id": step_id, "name": tc.name, "arguments": tc.arguments,
                }]))
                history.append(Message(role="tool", content=result, tool_call_id=step_id))
            continue

        if response.content:
            writer.log_assistant_response(response.content)
            print_response(response.content)
            return


async def main() -> None:
    parser = argparse.ArgumentParser(description="Week 3 — Replay Harness")
    parser.add_argument("--task", type=str, help="Run a fresh task")
    parser.add_argument("--replay", type=str, help="Path to session to replay from")
    parser.add_argument("--from-step", type=int, default=1, help="Step to fork from")
    parser.add_argument("--model", type=str, help="Model to use (overrides default)")
    args = parser.parse_args()

    print_header("Week 3 — Replay & Model-Swap", "Fork runs from any checkpoint")
    validate_setup()

    if args.task:
        session_id = datetime.now().strftime("%Y%m%d-%H%M%S")
        session_dir = Path("sessions") / session_id
        await run_fresh(args.task, session_dir, model=args.model)
        # Create a "latest" symlink
        latest = Path("sessions") / "latest"
        if latest.exists() or latest.is_symlink():
            latest.unlink()
        latest.symlink_to(session_dir.resolve())
        console.print(f"\n[dim]Session saved to: {session_dir}[/dim]")

    elif args.replay:
        source = Path(args.replay)
        replay_id = f"replay-{datetime.now().strftime('%H%M%S')}"
        target = Path("sessions") / replay_id
        await replay_from(source, args.from_step, target, model=args.model)
        console.print(f"\n[dim]Replay saved to: {target}[/dim]")

    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
