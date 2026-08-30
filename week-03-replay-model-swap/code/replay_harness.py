"""Run and replay checkpointed coding-agent sessions.

Replay starts after the requested completed tool step. The source checkpoint is
never modified; the fork stores the inherited event prefix plus its own new
events, so it is independently inspectable and replayable.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from shared.config import DEFAULT_MODEL, validate_setup
from shared.models import Message, get_provider
from shared.utils import console, print_header, print_response, print_tool_call, print_usage

from replay_core import RunMetrics, events_through_step, history_from_events, load_events, save_metrics

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "week-02-resumability-checkpoints" / "code"))
from checkpoint import CheckpointEvent, CheckpointWriter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "week-01-bare-agent-loop" / "code"))
from tools import TOOL_SCHEMAS, execute_tool


SYSTEM_PROMPT = """You are a helpful coding assistant. You can read files, write files, and run
shell commands to help the user with their coding tasks."""
MAX_ITERATIONS = 10


def copy_event_prefix(events: list[dict], writer: CheckpointWriter) -> None:
    """Copy inherited events into a fork log without changing their identity."""
    for event in events:
        writer.write(CheckpointEvent(
            event_type=event["event_type"], data=event["data"],
            timestamp=event.get("timestamp", datetime.now(timezone.utc).isoformat()),
            step_id=event.get("step_id", ""),
        ))


async def continue_run(history: list[Message], writer: CheckpointWriter, model: str) -> RunMetrics:
    """Execute the agent loop and write every new event through to disk."""
    started = time.perf_counter()
    metrics = RunMetrics(model=model)
    try:
        provider = get_provider(model=model)
        for _ in range(MAX_ITERATIONS):
            response = await provider.chat([Message(role="system", content=SYSTEM_PROMPT)] + history, tools=TOOL_SCHEMAS)
            metrics.add_usage(response.usage)
            print_usage(response.usage)
            if response.tool_calls:
                for tool_call in response.tool_calls:
                    metrics.tool_calls += 1
                    step_id = uuid.uuid4().hex[:8]
                    print_tool_call(tool_call.name, tool_call.arguments)
                    writer.log_tool_call(tool_call.name, tool_call.arguments, step_id)
                    result = execute_tool(tool_call.name, tool_call.arguments)
                    writer.log_tool_result(tool_call.name, result, step_id)
                    writer.log_step_complete(step_id)
                    history.append(Message(role="assistant", content="", tool_calls=[{
                        "id": step_id, "name": tool_call.name, "arguments": tool_call.arguments,
                    }]))
                    history.append(Message(role="tool", content=result, tool_call_id=step_id))
                continue
            if response.content:
                metrics.answer = response.content
                writer.log_assistant_response(response.content)
                print_response(response.content)
                break
        else:
            metrics.error = f"Reached {MAX_ITERATIONS} iterations without a final answer"
    except Exception as exc:
        metrics.error = str(exc)
        console.print(f"[red]Run failed: {exc}[/red]")
    finally:
        metrics.elapsed_seconds = time.perf_counter() - started
        save_metrics(writer.session_dir, metrics)
    return metrics


async def run_fresh(task: str, session_dir: Path, model: str) -> RunMetrics:
    session_dir.mkdir(parents=True, exist_ok=False)
    writer = CheckpointWriter(session_dir)
    writer.log_user_message(task)
    console.print(f"\n[bold]New run | Model: {model} | Session: {session_dir.name}[/bold]\n")
    return await continue_run([Message(role="user", content=task)], writer, model)


async def replay_from(source_dir: Path, from_step: int, target_dir: Path, model: str) -> RunMetrics:
    events = load_events(source_dir)
    prefix = events_through_step(events, from_step)
    target_dir.mkdir(parents=True, exist_ok=False)
    writer = CheckpointWriter(target_dir)
    copy_event_prefix(prefix, writer)
    writer.write(CheckpointEvent(event_type="replay_metadata", data={
        "source_session": str(source_dir.resolve()), "from_step": from_step, "model": model,
    }, step_id="replay"))
    console.print(f"\n[bold]Replay | From completed step {from_step} | Source: {source_dir.name} | Model: {model}[/bold]\n")
    return await continue_run(history_from_events(prefix), writer, model)


def session_name(prefix: str) -> str:
    return f"{prefix}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"


async def main() -> None:
    parser = argparse.ArgumentParser(description="Week 3 replay and model-swap harness")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--task", help="Run a fresh task")
    group.add_argument("--replay", help="Session directory to fork")
    parser.add_argument("--from-step", type=int, default=0, help="Completed tool step at which to fork (default: 0)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model for the fresh run or replay branch")
    parser.add_argument("--sessions-dir", default="sessions", help="Directory where run artifacts are stored")
    args = parser.parse_args()

    print_header("Week 3 — Replay & Model-Swap", "Fork a checkpoint without changing the original run")
    validate_setup()
    sessions_dir = Path(args.sessions_dir)
    if args.task:
        target = sessions_dir / session_name("run")
        await run_fresh(args.task, target, args.model)
        latest = sessions_dir / "latest"
        if latest.exists() or latest.is_symlink():
            latest.unlink()
        latest.symlink_to(target.resolve())
    else:
        target = sessions_dir / session_name("replay")
        await replay_from(Path(args.replay), args.from_step, target, args.model)
    console.print(f"\n[dim]Artifacts saved in: {target}[/dim]")


if __name__ == "__main__":
    asyncio.run(main())
