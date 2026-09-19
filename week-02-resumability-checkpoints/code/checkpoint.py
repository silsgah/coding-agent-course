"""
Week 2 — Checkpoint System
===========================

Persist agent state so a crashed run can resume without
re-executing already-completed work.

Uses an append-only JSONL file: each line is one event.
On resume, replay the log to rebuild history.

Inspired by the durable runtime in DecodingAI's coding agent
(src/decode/runtime/) and Kitaru's checkpoint model.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rich.console import Console

console = Console()


class CheckpointFormatError(ValueError):
    """Raised when a checkpoint cannot be safely replayed."""


# ---------------------------------------------------------------------------
# Checkpoint events
# ---------------------------------------------------------------------------
@dataclass
class CheckpointEvent:
    """A single event in the checkpoint log."""
    event_type: str          # user_message, tool_call, tool_result, assistant_response, step_complete
    data: dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    step_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])


# ---------------------------------------------------------------------------
# Checkpoint writer — append-only log
# ---------------------------------------------------------------------------
class CheckpointWriter:
    """Append events to a JSONL checkpoint file."""

    def __init__(self, session_dir: Path):
        self.session_dir = session_dir
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = session_dir / "checkpoint.jsonl"

    def write(self, event: CheckpointEvent) -> None:
        """Append and synchronously persist one event to the checkpoint log."""
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(event)) + "\n")
            f.flush()
            os.fsync(f.fileno())
        console.print(f"[dim]💾 Checkpoint: {event.event_type} ({event.step_id})[/dim]")

    def log_user_message(self, message: str) -> str:
        """Log a user message and return its step ID."""
        event = CheckpointEvent(
            event_type="user_message",
            data={"message": message},
        )
        self.write(event)
        return event.step_id

    def log_tool_call(self, tool_name: str, arguments: dict, step_id: str) -> None:
        """Log a tool call (what the model wants to do)."""
        self.write(CheckpointEvent(
            event_type="tool_call",
            data={"tool_name": tool_name, "arguments": arguments},
            step_id=step_id,
        ))

    def log_tool_result(self, tool_name: str, result: str, step_id: str) -> None:
        """Log a tool result (what the tool returned)."""
        self.write(CheckpointEvent(
            event_type="tool_result",
            data={"tool_name": tool_name, "result": result},
            step_id=step_id,
        ))

    def log_assistant_response(self, response: str) -> None:
        """Log the assistant's final text response."""
        self.write(CheckpointEvent(
            event_type="assistant_response",
            data={"response": response},
        ))

    def log_step_complete(self, step_id: str) -> None:
        """Mark a logical step as completed."""
        self.write(CheckpointEvent(
            event_type="step_complete",
            data={"completed": True},
            step_id=step_id,
        ))


# ---------------------------------------------------------------------------
# Checkpoint reader — replay log to rebuild state
# ---------------------------------------------------------------------------
@dataclass
class ResumeState:
    """State rebuilt from a checkpoint log."""
    messages: list[dict[str, Any]]       # Conversation history ready to send to model
    completed_steps: set[str]             # Step IDs that are done
    last_event_type: str | None = None    # What was the last thing that happened
    is_complete: bool = False             # Did the run finish?


class CheckpointReader:
    """Read a checkpoint log and rebuild agent state."""

    def __init__(self, session_dir: Path):
        self.log_path = session_dir / "checkpoint.jsonl"

    def has_checkpoint(self) -> bool:
        """Check if a checkpoint exists."""
        return self.log_path.exists() and self.log_path.stat().st_size > 0

    def load(self) -> ResumeState:
        """Replay the checkpoint log and return the rebuilt state."""
        state = ResumeState(messages=[], completed_steps=set())

        if not self.has_checkpoint():
            return state

        events = self._read_events()

        console.print(f"\n[bold cyan]📂 Resuming from checkpoint ({len(events)} events)...[/bold cyan]")

        for event in events:
            event_type = event["event_type"]
            data = event["data"]
            step_id = event.get("step_id", "")

            state.last_event_type = event_type

            if event_type == "user_message":
                state.messages.append({
                    "role": "user",
                    "content": data["message"],
                })

            elif event_type == "tool_call":
                state.messages.append({
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [{
                        "id": step_id,
                        "name": data["tool_name"],
                        "arguments": data["arguments"],
                    }],
                })

            elif event_type == "tool_result":
                state.messages.append({
                    "role": "tool",
                    "content": data["result"],
                    "tool_call_id": step_id,
                })

            elif event_type == "assistant_response":
                state.messages.append({
                    "role": "assistant",
                    "content": data["response"],
                })
                state.is_complete = True

            elif event_type == "step_complete":
                state.completed_steps.add(step_id)

        # ── Handle dangling tool_calls ────────────────────────────
        # If the process crashed after logging a tool_call but before
        # executing it (no tool_result), the last message will be an
        # assistant message with a tool_call and no matching tool result.
        # The model API requires every tool_call to have a tool result,
        # so we strip dangling ones to let the model re-decide.
        while (
            state.messages
            and state.messages[-1].get("role") == "assistant"
            and state.messages[-1].get("tool_calls")
        ):
            dangling = state.messages[-1]["tool_calls"][0]
            console.print(
                f"[yellow]⚠️  Stripping dangling tool_call: "
                f"{dangling['name']} (crashed before execution)[/yellow]"
            )
            state.messages.pop()

        console.print(f"[green]✅ Rebuilt {len(state.messages)} messages, "
                      f"{len(state.completed_steps)} completed steps[/green]")

        return state

    def _read_events(self) -> list[dict[str, Any]]:
        """Read validated JSONL events, ignoring only a torn final record.

        A crash can interrupt the final append and leave one incomplete JSON
        line. Earlier malformed lines are unsafe because later events may
        depend on them, so those fail with an actionable line number.
        """
        with open(self.log_path, encoding="utf-8") as f:
            lines = [(number, line.strip()) for number, line in enumerate(f, 1)]
        lines = [(number, line) for number, line in lines if line]

        events: list[dict[str, Any]] = []
        known_types = {
            "user_message",
            "tool_call",
            "tool_result",
            "assistant_response",
            "step_complete",
        }
        for index, (line_number, line) in enumerate(lines):
            try:
                event = json.loads(line)
            except json.JSONDecodeError as error:
                if index == len(lines) - 1:
                    console.print(
                        "[yellow]⚠️  Ignoring torn final checkpoint record "
                        f"on line {line_number}[/yellow]"
                    )
                    break
                raise CheckpointFormatError(
                    f"Invalid JSON on checkpoint line {line_number}: {error.msg}"
                ) from error

            if not isinstance(event, dict):
                raise CheckpointFormatError(
                    f"Checkpoint line {line_number} must be a JSON object"
                )
            if event.get("event_type") not in known_types:
                raise CheckpointFormatError(
                    f"Unknown event type on checkpoint line {line_number}"
                )
            if not isinstance(event.get("data"), dict):
                raise CheckpointFormatError(
                    f"Checkpoint line {line_number} has invalid event data"
                )
            self._validate_event(event, line_number)
            events.append(event)

        return events

    @staticmethod
    def _validate_event(event: dict[str, Any], line_number: int) -> None:
        """Validate fields needed to rebuild a provider-compatible history."""
        required_fields = {
            "user_message": {"message"},
            "tool_call": {"tool_name", "arguments"},
            "tool_result": {"tool_name", "result"},
            "assistant_response": {"response"},
            "step_complete": {"completed"},
        }
        event_type = event["event_type"]
        missing = required_fields[event_type] - event["data"].keys()
        if missing:
            fields = ", ".join(sorted(missing))
            raise CheckpointFormatError(
                f"Checkpoint line {line_number} is missing required field(s): {fields}"
            )
        if event_type in {"tool_call", "tool_result", "step_complete"}:
            step_id = event.get("step_id")
            if not isinstance(step_id, str) or not step_id:
                raise CheckpointFormatError(
                    f"Checkpoint line {line_number} has no usable step_id"
                )
        if event_type == "tool_call" and not isinstance(
            event["data"]["arguments"], dict
        ):
            raise CheckpointFormatError(
                f"Checkpoint line {line_number} has non-object tool arguments"
            )
