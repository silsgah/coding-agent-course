"""
Week 3 — Model Swap Comparison
================================

Run the same task from the same starting point with multiple models,
then output a comparison table.

Usage:
    python model_swap.py
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from shared.config import validate_setup
from shared.models import get_provider, Message
from shared.utils import print_header, console

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "week-01-bare-agent-loop" / "code"))
from tools import TOOL_SCHEMAS, execute_tool


SYSTEM_PROMPT = """\
You are a helpful coding assistant. Complete the task efficiently.
"""

DEMO_TASK = (
    "List the Python files in the current directory, then create a brief "
    "summary of what this project does based on the file names."
)


@dataclass
class RunResult:
    """Result from one model run."""
    model: str
    answer: str
    tool_calls: int
    prompt_tokens: int
    completion_tokens: int
    elapsed_seconds: float
    error: str | None = None


async def run_with_model(task: str, model: str) -> RunResult:
    """Run a task with a specific model and return metrics."""
    start_time = time.perf_counter()
    tool_call_count = 0
    total_prompt = 0
    total_completion = 0

    try:
        provider = get_provider(model=model)
        history = [
            Message(role="system", content=SYSTEM_PROMPT),
            Message(role="user", content=task),
        ]

        for iteration in range(10):
            response = await provider.chat(history, tools=TOOL_SCHEMAS)
            total_prompt += response.usage.get("prompt_tokens", 0)
            total_completion += response.usage.get("completion_tokens", 0)

            if response.tool_calls:
                for tc in response.tool_calls:
                    tool_call_count += 1
                    result = execute_tool(tc.name, tc.arguments)
                    history.append(Message(
                        role="assistant", content="",
                        tool_calls=[{"id": tc.id, "name": tc.name, "arguments": tc.arguments}],
                    ))
                    history.append(Message(role="tool", content=result, tool_call_id=tc.id))
                continue

            if response.content:
                return RunResult(
                    model=model,
                    answer=response.content,
                    tool_calls=tool_call_count,
                    prompt_tokens=total_prompt,
                    completion_tokens=total_completion,
                    elapsed_seconds=time.perf_counter() - start_time,
                )

        return RunResult(
            model=model,
            answer="(reached max iterations)",
            tool_calls=tool_call_count,
            prompt_tokens=total_prompt,
            completion_tokens=total_completion,
            elapsed_seconds=time.perf_counter() - start_time,
        )

    except Exception as e:
        return RunResult(
            model=model,
            answer="",
            tool_calls=tool_call_count,
            prompt_tokens=total_prompt,
            completion_tokens=total_completion,
            elapsed_seconds=time.perf_counter() - start_time,
            error=str(e),
        )


async def main() -> None:
    print_header(
        "Week 3 — Model Swap Comparison",
        "Same task, same tools, different models",
    )
    validate_setup()

    # Models to compare — adjust based on your API keys
    models = [
        "gemini-2.5-flash",
        # Uncomment if you have the API keys:
        # "gemini-2.5-pro",
        # "gpt-4o-mini",
        # "claude-haiku-4-5",
    ]

    console.print(f"\n[bold]Task:[/bold] {DEMO_TASK}")
    console.print(f"[bold]Models:[/bold] {', '.join(models)}\n")

    results: list[RunResult] = []
    for model in models:
        console.print(f"[cyan]Running with {model}...[/cyan]")
        result = await run_with_model(DEMO_TASK, model)
        results.append(result)
        if result.error:
            console.print(f"[red]  Error: {result.error}[/red]")
        else:
            console.print(f"[green]  Done in {result.elapsed_seconds:.1f}s, "
                          f"{result.tool_calls} tool calls[/green]")

    # Print comparison table
    console.print("\n[bold]═══ Comparison Report ═══[/bold]\n")

    from rich.table import Table
    table = Table(title="Model Comparison", show_lines=True)
    table.add_column("Metric", style="bold")
    for r in results:
        table.add_column(r.model, justify="center")

    table.add_row("Tool Calls", *[str(r.tool_calls) for r in results])
    table.add_row("Prompt Tokens", *[str(r.prompt_tokens) for r in results])
    table.add_row("Completion Tokens", *[str(r.completion_tokens) for r in results])
    table.add_row("Total Tokens", *[str(r.prompt_tokens + r.completion_tokens) for r in results])
    table.add_row("Time (seconds)", *[f"{r.elapsed_seconds:.1f}" for r in results])
    table.add_row("Error", *[r.error or "—" for r in results])

    console.print(table)

    # Print answers side by side
    console.print("\n[bold]═══ Answers ═══[/bold]")
    for r in results:
        console.print(f"\n[bold cyan]── {r.model} ──[/bold cyan]")
        console.print(r.answer[:500] if r.answer else "(no answer)")


if __name__ == "__main__":
    asyncio.run(main())
