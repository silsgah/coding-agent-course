"""
Shared utilities for the Coding Agent Course.

Small helpers that show up in more than one week.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax

console = Console()


# ---------------------------------------------------------------------------
# Pretty printing helpers
# ---------------------------------------------------------------------------
def print_header(title: str, subtitle: str = "") -> None:
    """Print a styled course header."""
    content = f"[bold cyan]{title}[/bold cyan]"
    if subtitle:
        content += f"\n[dim]{subtitle}[/dim]"
    console.print(Panel(content, border_style="cyan", padding=(1, 2)))


def print_step(step: int, description: str) -> None:
    """Print a numbered step in a workflow."""
    console.print(f"\n[bold yellow]Step {step}:[/bold yellow] {description}")


def print_tool_call(name: str, args: dict[str, Any]) -> None:
    """Print a tool call in a readable format."""
    console.print(f"\n🔧 [bold magenta]Tool Call:[/bold magenta] {name}")
    if args:
        console.print(Syntax(json.dumps(args, indent=2), "json", theme="monokai"))


def print_response(content: str) -> None:
    """Print an assistant response as rendered Markdown."""
    console.print(Panel(Markdown(content), title="🤖 Assistant", border_style="green"))


def print_usage(usage: dict[str, int]) -> None:
    """Print token usage stats."""
    prompt = usage.get("prompt_tokens", 0)
    completion = usage.get("completion_tokens", 0)
    total = prompt + completion
    console.print(
        f"[dim]📊 Tokens — prompt: {prompt}, completion: {completion}, total: {total}[/dim]"
    )


# ---------------------------------------------------------------------------
# Session logging
# ---------------------------------------------------------------------------
def log_event(
    session_dir: Path,
    event_type: str,
    data: dict[str, Any],
) -> None:
    """Append a JSON event to the session log (JSONL format)."""
    session_dir.mkdir(parents=True, exist_ok=True)
    log_file = session_dir / "session.jsonl"

    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": event_type,
        **data,
    }
    with open(log_file, "a") as f:
        f.write(json.dumps(event) + "\n")


def load_session(session_dir: Path) -> list[dict[str, Any]]:
    """Load all events from a session log."""
    log_file = session_dir / "session.jsonl"
    if not log_file.exists():
        return []
    events = []
    with open(log_file) as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    return events


# ---------------------------------------------------------------------------
# Timing
# ---------------------------------------------------------------------------
class Timer:
    """Simple context manager for timing operations."""

    def __init__(self, label: str = ""):
        self.label = label
        self.elapsed: float = 0.0

    def __enter__(self) -> "Timer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, *args: Any) -> None:
        self.elapsed = time.perf_counter() - self._start
        if self.label:
            console.print(f"[dim]⏱️  {self.label}: {self.elapsed:.2f}s[/dim]")
