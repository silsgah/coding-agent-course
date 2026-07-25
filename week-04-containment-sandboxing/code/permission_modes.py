"""
Week 4 — Permission Modes
===========================

Four graduated permission modes that replace the Week 1 y/n gate:
  - deny-all:   Nothing executes (review mode)
  - ask-all:    Everything asks (Week 1 behavior)
  - auto-read:  Reads auto-approve, writes ask
  - full-trust: Everything auto-approves (use with sandbox!)

Usage:
    python permission_modes.py --mode auto-read

Inspired by the permission system in DecodingAI's coding agent
(src/decode/permissions/).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from enum import Enum
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from shared.config import validate_setup, DEFAULT_MODEL
from shared.models import get_provider, Message
from shared.utils import print_header, print_tool_call, print_response, print_usage, console

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "week-01-bare-agent-loop" / "code"))
from tools import TOOLS, TOOL_SCHEMAS, execute_tool

from rich.panel import Panel
from rich.syntax import Syntax


# ---------------------------------------------------------------------------
# Permission modes
# ---------------------------------------------------------------------------
class PermissionMode(str, Enum):
    DENY_ALL = "deny-all"
    ASK_ALL = "ask-all"
    AUTO_READ = "auto-read"
    FULL_TRUST = "full-trust"


# Tool categories
TOOL_CATEGORIES = {
    "read_file": "read",
    "list_dir": "read",
    "bash": "write",       # bash can do anything — treat as write
    "write_file": "write",
}

# Mode → category → action
MODE_RULES: dict[PermissionMode, dict[str, str]] = {
    PermissionMode.DENY_ALL: {
        "read": "deny",
        "write": "deny",
    },
    PermissionMode.ASK_ALL: {
        "read": "ask",
        "write": "ask",
    },
    PermissionMode.AUTO_READ: {
        "read": "allow",
        "write": "ask",
    },
    PermissionMode.FULL_TRUST: {
        "read": "allow",
        "write": "allow",
    },
}


class PermissionGate:
    """Mode-aware permission gate for tool calls."""

    def __init__(self, mode: PermissionMode):
        self.mode = mode
        self.stats = {"allowed": 0, "denied": 0, "asked": 0}

    def check(self, tool_name: str, arguments: dict[str, Any]) -> bool:
        """Check if a tool call is permitted under the current mode."""
        category = TOOL_CATEGORIES.get(tool_name, "write")
        action = MODE_RULES[self.mode].get(category, "ask")

        if action == "allow":
            self.stats["allowed"] += 1
            console.print(f"[green]✅ Auto-approved: {tool_name} (mode: {self.mode.value})[/green]")
            return True

        elif action == "deny":
            self.stats["denied"] += 1
            console.print(f"[red]🚫 Blocked: {tool_name} (mode: {self.mode.value})[/red]")
            return False

        else:  # ask
            self.stats["asked"] += 1
            return self._ask_user(tool_name, arguments)

    def _ask_user(self, tool_name: str, arguments: dict[str, Any]) -> bool:
        """Interactive approval prompt."""
        risk_colors = {"read": "green", "write": "red"}
        category = TOOL_CATEGORIES.get(tool_name, "write")
        color = risk_colors.get(category, "yellow")

        console.print(Panel(
            f"[bold]Tool:[/bold] {tool_name}\n"
            f"[bold]Category:[/bold] [{color}]{category}[/{color}]\n"
            f"[bold]Mode:[/bold] {self.mode.value}",
            title="🔐 Permission Required",
            border_style=color,
        ))
        console.print(Syntax(json.dumps(arguments, indent=2), "json", theme="monokai"))

        while True:
            try:
                resp = console.input(f"\n[bold {color}]Allow? (y/n):[/bold {color}] ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                return False
            if resp in ("y", "yes"):
                return True
            if resp in ("n", "no"):
                return False

    def print_stats(self) -> None:
        """Print permission statistics."""
        console.print(f"\n[dim]📊 Permission stats (mode: {self.mode.value}): "
                      f"allowed={self.stats['allowed']}, "
                      f"asked={self.stats['asked']}, "
                      f"denied={self.stats['denied']}[/dim]")


# ---------------------------------------------------------------------------
# Agent loop with permission modes
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """\
You are a helpful coding assistant. You can read files, write files, and run
shell commands to help the user.
"""


async def agent_loop(
    user_message: str,
    history: list[Message],
    gate: PermissionGate,
) -> str:
    """Agent loop with mode-aware permission gate."""
    provider = get_provider()
    history.append(Message(role="user", content=user_message))

    for iteration in range(10):
        messages = [Message(role="system", content=SYSTEM_PROMPT)] + history
        response = await provider.chat(messages, tools=TOOL_SCHEMAS)
        print_usage(response.usage)

        if response.tool_calls:
            for tc in response.tool_calls:
                print_tool_call(tc.name, tc.arguments)

                # Use the mode-aware gate
                if gate.check(tc.name, tc.arguments):
                    result = execute_tool(tc.name, tc.arguments)
                else:
                    result = f"⛔ Tool '{tc.name}' blocked by permission mode '{gate.mode.value}'."

                history.append(Message(
                    role="assistant", content="",
                    tool_calls=[{"id": tc.id, "name": tc.name, "arguments": tc.arguments}],
                ))
                history.append(Message(role="tool", content=result, tool_call_id=tc.id))
            continue

        if response.content:
            history.append(Message(role="assistant", content=response.content))
            return response.content

    return "⚠️ Max iterations reached."


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        type=str,
        choices=[m.value for m in PermissionMode],
        default="auto-read",
        help="Permission mode (default: auto-read)",
    )
    args = parser.parse_args()

    mode = PermissionMode(args.mode)
    gate = PermissionGate(mode)

    print_header(
        "Week 4 — Permission Modes",
        f"Mode: {mode.value} | Model: {DEFAULT_MODEL}",
    )
    validate_setup()

    mode_desc = {
        PermissionMode.DENY_ALL: "🚫 All tools blocked — review mode only",
        PermissionMode.ASK_ALL: "🔐 Every tool call requires approval",
        PermissionMode.AUTO_READ: "📖 Reads auto-approved, writes require approval",
        PermissionMode.FULL_TRUST: "⚡ Everything auto-approved — USE WITH SANDBOX!",
    }
    console.print(f"\n{mode_desc[mode]}\n")

    history: list[Message] = []

    while True:
        try:
            user_input = console.input("\n[bold cyan]You:[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input or user_input.lower() in ("quit", "exit", "q"):
            break

        response = await agent_loop(user_input, history, gate)
        print_response(response)

    gate.print_stats()


if __name__ == "__main__":
    asyncio.run(main())
