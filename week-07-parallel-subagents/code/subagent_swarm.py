"""
Week 7 — Subagent Swarm
=========================

Fan out one task into N child agents, each running in parallel
with its own context, budget, and structured report contract.

Inspired by:
- DecodingAI's Explore subagent (src/decode/agents/)
- NOOA's self-extending agents with asyncio.gather fan-out
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from shared.config import validate_setup, DEFAULT_MODEL
from shared.models import get_provider, Message
from shared.utils import print_header, print_response, console

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "week-01-bare-agent-loop" / "code"))
from tools import TOOL_SCHEMAS, execute_tool


# ---------------------------------------------------------------------------
# Structured report from each child agent
# ---------------------------------------------------------------------------
@dataclass
class SubagentReport:
    """What each child agent must return."""
    subtask: str
    status: str            # "success", "partial", "failed"
    summary: str           # One-paragraph summary of findings
    key_facts: list[str]   # Bullet points
    tokens_used: int
    tool_calls: int
    elapsed_seconds: float
    error: str | None = None


# ---------------------------------------------------------------------------
# Child agent — runs one subtask independently
# ---------------------------------------------------------------------------
async def run_child_agent(
    subtask: str,
    agent_id: int,
    max_tokens: int = 8_000,
) -> SubagentReport:
    """
    Run a single child agent on a subtask.

    Each child gets:
    - Its own context (fresh conversation)
    - A token budget
    - A requirement to return a structured report
    """
    start_time = time.perf_counter()
    tool_calls = 0
    total_tokens = 0

    console.print(f"[cyan]  🤖 Child {agent_id} started: {subtask[:60]}...[/cyan]")

    try:
        provider = get_provider()
        history = [
            Message(
                role="system",
                content=(
                    f"You are agent #{agent_id}. Complete this specific subtask:\n\n"
                    f"{subtask}\n\n"
                    "Be thorough but concise. Focus only on your assigned subtask."
                ),
            ),
            Message(role="user", content=subtask),
        ]

        for iteration in range(6):  # Limit iterations per child
            response = await provider.chat(history, tools=TOOL_SCHEMAS)
            prompt_tokens = response.usage.get("prompt_tokens", 0)
            comp_tokens = response.usage.get("completion_tokens", 0)
            total_tokens += prompt_tokens + comp_tokens

            # Budget check
            if total_tokens > max_tokens:
                return SubagentReport(
                    subtask=subtask,
                    status="partial",
                    summary="Exceeded token budget before completing.",
                    key_facts=["Budget exceeded"],
                    tokens_used=total_tokens,
                    tool_calls=tool_calls,
                    elapsed_seconds=time.perf_counter() - start_time,
                )

            if response.tool_calls:
                for tc in response.tool_calls:
                    tool_calls += 1
                    result = execute_tool(tc.name, tc.arguments)
                    history.append(Message(
                        role="assistant", content="",
                        tool_calls=[{"id": tc.id, "name": tc.name, "arguments": tc.arguments}],
                    ))
                    history.append(Message(role="tool", content=result, tool_call_id=tc.id))
                continue

            if response.content:
                elapsed = time.perf_counter() - start_time
                console.print(f"[green]  ✅ Child {agent_id} done ({elapsed:.1f}s, "
                              f"{total_tokens} tokens)[/green]")
                return SubagentReport(
                    subtask=subtask,
                    status="success",
                    summary=response.content[:500],
                    key_facts=[line.strip("- ") for line in response.content.split("\n")
                               if line.strip().startswith("-")][:5],
                    tokens_used=total_tokens,
                    tool_calls=tool_calls,
                    elapsed_seconds=elapsed,
                )

        return SubagentReport(
            subtask=subtask, status="partial",
            summary="Max iterations reached.",
            key_facts=[], tokens_used=total_tokens,
            tool_calls=tool_calls,
            elapsed_seconds=time.perf_counter() - start_time,
        )

    except Exception as e:
        return SubagentReport(
            subtask=subtask, status="failed",
            summary="", key_facts=[],
            tokens_used=total_tokens, tool_calls=tool_calls,
            elapsed_seconds=time.perf_counter() - start_time,
            error=str(e),
        )


# ---------------------------------------------------------------------------
# Coordinator — decompose, fan out, merge
# ---------------------------------------------------------------------------
async def decompose_task(task: str) -> list[str]:
    """Use the model to decompose a task into independent subtasks."""
    provider = get_provider()
    response = await provider.chat([
        Message(
            role="system",
            content=(
                "You are a task decomposer. Break the given task into 3-5 independent subtasks. "
                "Each subtask should be completable on its own without depending on other subtasks. "
                "Return ONLY a JSON array of strings, nothing else."
            ),
        ),
        Message(role="user", content=task),
    ])

    try:
        # Try to parse as JSON array
        text = response.content.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        subtasks = json.loads(text)
        if isinstance(subtasks, list):
            return [str(s) for s in subtasks]
    except (json.JSONDecodeError, IndexError):
        pass

    # Fallback: split by newlines
    return [line.strip("- ").strip() for line in response.content.split("\n")
            if line.strip() and not line.strip().startswith("```")]


async def merge_reports(task: str, reports: list[SubagentReport]) -> str:
    """Merge child reports into a final answer."""
    provider = get_provider()

    reports_text = "\n\n".join(
        f"### Subtask: {r.subtask}\n"
        f"Status: {r.status}\n"
        f"Summary: {r.summary}\n"
        f"Key facts: {', '.join(r.key_facts)}"
        for r in reports
    )

    response = await provider.chat([
        Message(
            role="system",
            content="You are a report merger. Combine the following subtask reports into a "
                    "single coherent answer to the original task. Be concise.",
        ),
        Message(
            role="user",
            content=f"Original task: {task}\n\nSubtask reports:\n\n{reports_text}",
        ),
    ])
    return response.content


async def run_swarm(task: str) -> None:
    """Run the full coordinator → fan-out → merge pipeline."""
    console.print(f"\n[bold]Original task:[/bold] {task}\n")

    # Step 1: Decompose
    console.print("[bold yellow]Step 1: Decomposing task...[/bold yellow]")
    subtasks = await decompose_task(task)
    for i, st in enumerate(subtasks, 1):
        console.print(f"  {i}. {st}")

    # Step 2: Fan out
    console.print(f"\n[bold yellow]Step 2: Launching {len(subtasks)} child agents in parallel...[/bold yellow]")
    start = time.perf_counter()

    reports = await asyncio.gather(*[
        run_child_agent(subtask, i + 1) for i, subtask in enumerate(subtasks)
    ])

    elapsed = time.perf_counter() - start
    console.print(f"\n[bold]All children complete in {elapsed:.1f}s[/bold]")

    # Step 3: Merge
    console.print("\n[bold yellow]Step 3: Merging reports...[/bold yellow]")
    final_answer = await merge_reports(task, list(reports))
    print_response(final_answer)

    # Stats
    from rich.table import Table
    table = Table(title="Subagent Statistics", show_lines=True)
    table.add_column("Agent", justify="center")
    table.add_column("Status", justify="center")
    table.add_column("Tokens", justify="right")
    table.add_column("Tools", justify="right")
    table.add_column("Time", justify="right")

    for i, r in enumerate(reports, 1):
        status_color = {"success": "green", "partial": "yellow", "failed": "red"}.get(r.status, "white")
        table.add_row(
            f"Child {i}", f"[{status_color}]{r.status}[/{status_color}]",
            str(r.tokens_used), str(r.tool_calls), f"{r.elapsed_seconds:.1f}s",
        )

    total_tokens = sum(r.tokens_used for r in reports)
    total_tools = sum(r.tool_calls for r in reports)
    table.add_row("[bold]Total[/bold]", "", f"[bold]{total_tokens}[/bold]",
                  f"[bold]{total_tools}[/bold]", f"[bold]{elapsed:.1f}s[/bold]")

    console.print(table)


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------
async def main() -> None:
    print_header("Week 7 — Subagent Swarm", "Parallel fan-out with structured reports")
    validate_setup()

    demo_task = (
        "Explore this project thoroughly: list all Python files, read the README, "
        "check for a requirements.txt, look for test files, and summarize the "
        "project structure and purpose."
    )

    await run_swarm(demo_task)


if __name__ == "__main__":
    asyncio.run(main())
