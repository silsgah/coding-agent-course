"""Pure helpers for Week 3 replay sessions.

Keeping checkpoint parsing and report data separate from model calls makes the
replay harness easy to test and useful with every supported provider.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from shared.models import Message


@dataclass
class RunMetrics:
    """Metrics accumulated while an agent run is executing."""

    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    tool_calls: int = 0
    elapsed_seconds: float = 0.0
    answer: str = ""
    error: str | None = None
    temperature: float | None = None

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def add_usage(self, usage: dict[str, int]) -> None:
        self.prompt_tokens += usage.get("prompt_tokens", usage.get("input_tokens", 0)) or 0
        self.completion_tokens += usage.get("completion_tokens", usage.get("output_tokens", 0)) or 0


def checkpoint_path(session_dir: Path) -> Path:
    return session_dir / "checkpoint.jsonl"


def load_events(session_dir: Path) -> list[dict[str, Any]]:
    """Load JSONL checkpoint events, with a useful error for malformed logs."""
    path = checkpoint_path(session_dir)
    if not path.exists():
        raise FileNotFoundError(f"Checkpoint not found: {path}")

    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in {path} at line {line_number}") from exc
    return events


def events_through_step(events: list[dict[str, Any]], completed_steps: int) -> list[dict[str, Any]]:
    """Return the exact event prefix ending at the requested completed step.

    ``0`` means the state immediately after the initial user message. A step
    is counted only when its ``step_complete`` event is reached.
    """
    if completed_steps < 0:
        raise ValueError("from_step must be zero or greater")

    if completed_steps == 0:
        # A fresh run begins with its user message. Keeping exactly that event
        # gives the alternate model the original request but none of the
        # original model's decisions.
        return [event for event in events if event["event_type"] == "user_message"][:1]

    prefix: list[dict[str, Any]] = []
    seen_steps = 0
    for event in events:
        if event["event_type"] == "assistant_response":
            break
        prefix.append(event)
        if event["event_type"] == "step_complete":
            seen_steps += 1
            if seen_steps == completed_steps:
                return prefix

    if completed_steps > seen_steps:
        raise ValueError(f"Checkpoint contains {seen_steps} completed step(s), not {completed_steps}")
    return prefix


def history_from_events(events: list[dict[str, Any]]) -> list[Message]:
    """Convert checkpoint events to provider-neutral conversation messages."""
    history: list[Message] = []
    for event in events:
        event_type, data, step_id = event["event_type"], event["data"], event.get("step_id", "")
        if event_type == "user_message":
            history.append(Message(role="user", content=data["message"]))
        elif event_type == "tool_call":
            history.append(Message(role="assistant", content="", tool_calls=[{
                "id": step_id, "name": data["tool_name"], "arguments": data["arguments"],
            }]))
        elif event_type == "tool_result":
            history.append(Message(role="tool", content=data["result"], tool_call_id=step_id))
        elif event_type == "assistant_response":
            history.append(Message(role="assistant", content=data["response"]))
    return history


def save_metrics(session_dir: Path, metrics: RunMetrics) -> Path:
    """Persist a small, portable summary next to the checkpoint log."""
    path = session_dir / "run_metrics.json"
    path.write_text(json.dumps(asdict(metrics) | {"total_tokens": metrics.total_tokens}, indent=2) + "\n", encoding="utf-8")
    return path


def load_metrics(session_dir: Path) -> dict[str, Any]:
    path = session_dir / "run_metrics.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))
