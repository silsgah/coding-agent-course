"""
Week 1 — Permission Gate
=========================

The simplest possible human-in-the-loop safety mechanism:
before ANY tool executes, show the user what the agent wants
to do and ask y/n.

This is the FIRST harness component. It's primitive, but it's
already more safety than most agent tutorials teach.

In Week 4, we upgrade this to four permission modes:
  1. full-trust  — everything auto-approved
  2. auto-read   — reads auto-approved, writes ask
  3. ask-all     — everything asks (this week's behavior)
  4. deny-all    — nothing executes (read-only agent)

Inspired by the permission system in DecodingAI's coding agent
(src/decode/permissions/).
"""

from __future__ import annotations

import json
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

console = Console()


# ---------------------------------------------------------------------------
# Risk classification — used for display, upgraded in Week 4
# ---------------------------------------------------------------------------
RISK_LEVELS = {
    "read_file": "low",     # Reading is generally safe
    "write_file": "medium", # Writing changes state
    "bash": "high",         # Shell commands can do anything
}

RISK_COLORS = {
    "low": "green",
    "medium": "yellow",
    "high": "red",
}


def ask_permission(tool_name: str, arguments: dict[str, Any]) -> bool:
    """
    Ask the user whether to allow a tool call.

    Displays the tool name, arguments, and risk level,
    then waits for y/n input.

    Args:
        tool_name: Name of the tool the agent wants to call.
        arguments: Arguments the agent wants to pass.

    Returns:
        True if the user approves, False if they deny.
    """
    risk = RISK_LEVELS.get(tool_name, "medium")
    color = RISK_COLORS[risk]

    # Build the display
    args_display = json.dumps(arguments, indent=2)

    panel_content = (
        f"[bold]Tool:[/bold] {tool_name}\n"
        f"[bold]Risk:[/bold] [{color}]{risk}[/{color}]\n"
        f"[bold]Arguments:[/bold]\n"
    )

    console.print(Panel(panel_content, title="🔐 Permission Required", border_style=color))
    console.print(Syntax(args_display, "json", theme="monokai"))

    # Ask for approval
    while True:
        try:
            response = console.input(
                f"\n[bold {color}]Allow this tool call? (y/n):[/bold {color}] "
            ).strip().lower()
        except (EOFError, KeyboardInterrupt):
            return False

        if response in ("y", "yes"):
            return True
        elif response in ("n", "no"):
            return False
        else:
            console.print("[dim]Please enter 'y' or 'n'[/dim]")
