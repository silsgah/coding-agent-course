"""
Week 8 — Benchmark Suite
==========================

Repeatable task evaluation for coding agents.

Defines tasks with expected outcomes and scores agent performance:
- Did the file get created with correct content?
- Did the agent use the right tools?
- Was the answer accurate?

Inspired by:
- DecodingAI's eval framework (evals/)
- NOOA's benchmark methodology
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
import tempfile
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from shared.config import validate_setup, DEFAULT_MODEL
from shared.models import get_provider, Message
from shared.utils import print_header, console

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "week-01-bare-agent-loop" / "code"))
from tools import TOOL_SCHEMAS, execute_tool

from rich.table import Table


# ---------------------------------------------------------------------------
# Benchmark task definitions
# ---------------------------------------------------------------------------
@dataclass
class BenchmarkTask:
    """A single benchmark task with expected outcome."""
    name: str
    prompt: str
    validator: str  # Python expression to validate (using `result` and `workspace`)
    category: str = "general"
    max_tokens: int = 10_000
    max_iterations: int = 8


@dataclass
class BenchmarkResult:
    """Result of running one benchmark task."""
    task_name: str
    passed: bool
    score: float  # 0.0 to 1.0
    tokens_used: int
    tool_calls: int
    elapsed_seconds: float
    error: str | None = None
    agent_answer: str = ""


# Built-in benchmark tasks
BENCHMARK_TASKS = [
    BenchmarkTask(
        name="create_file",
        prompt="Create a file called 'hello.py' with a function called 'greet' that takes a name parameter and returns 'Hello, {name}!'",
        validator="(workspace / 'hello.py').exists() and 'def greet' in (workspace / 'hello.py').read_text()",
        category="file_creation",
    ),
    BenchmarkTask(
        name="list_and_summarize",
        prompt="List all files in the current directory and tell me how many there are.",
        validator="any(c.isdigit() for c in result)",  # Answer should contain a number
        category="exploration",
    ),
    BenchmarkTask(
        name="read_and_extract",
        prompt="Read the file 'test_data.txt' and tell me the total of all the numbers in it.",
        validator="'15' in result",  # 1+2+3+4+5 = 15
        category="analysis",
    ),
    BenchmarkTask(
        name="multi_step",
        prompt="Create a directory called 'output', then create three files in it: a.txt, b.txt, c.txt, each containing their own filename.",
        validator="all((workspace / 'output' / f).exists() for f in ['a.txt', 'b.txt', 'c.txt'])",
        category="multi_step",
    ),
    BenchmarkTask(
        name="error_handling",
        prompt="Try to read a file called 'nonexistent_file_xyz.txt' and gracefully report that it doesn't exist.",
        validator="'not' in result.lower() or 'error' in result.lower() or 'exist' in result.lower()",
        category="error_handling",
    ),
]


# ---------------------------------------------------------------------------
# Benchmark runner
# ---------------------------------------------------------------------------
async def run_benchmark_task(
    task: BenchmarkTask,
    workspace: Path,
) -> BenchmarkResult:
    """Run a single benchmark task and evaluate the result."""
    start = time.perf_counter()
    total_tokens = 0
    tool_calls = 0

    try:
        provider = get_provider()
        history = [
            Message(role="system", content="You are a coding assistant. Complete the task precisely."),
            Message(role="user", content=task.prompt),
        ]

        for iteration in range(task.max_iterations):
            response = await provider.chat(history, tools=TOOL_SCHEMAS)
            total_tokens += (
                response.usage.get("prompt_tokens", 0) +
                response.usage.get("completion_tokens", 0)
            )

            if total_tokens > task.max_tokens:
                break

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
                result = response.content
                elapsed = time.perf_counter() - start

                # Validate
                try:
                    passed = eval(task.validator, {"result": result, "workspace": workspace})
                except Exception as e:
                    passed = False

                return BenchmarkResult(
                    task_name=task.name,
                    passed=bool(passed),
                    score=1.0 if passed else 0.0,
                    tokens_used=total_tokens,
                    tool_calls=tool_calls,
                    elapsed_seconds=elapsed,
                    agent_answer=result[:200],
                )

        return BenchmarkResult(
            task_name=task.name, passed=False, score=0.0,
            tokens_used=total_tokens, tool_calls=tool_calls,
            elapsed_seconds=time.perf_counter() - start,
            error="Max iterations reached",
        )

    except Exception as e:
        return BenchmarkResult(
            task_name=task.name, passed=False, score=0.0,
            tokens_used=total_tokens, tool_calls=tool_calls,
            elapsed_seconds=time.perf_counter() - start,
            error=str(e),
        )


async def run_benchmark_suite(tasks: list[BenchmarkTask] | None = None) -> list[BenchmarkResult]:
    """Run all benchmark tasks and return results."""
    tasks = tasks or BENCHMARK_TASKS
    results = []

    for task in tasks:
        # Each task gets a fresh workspace
        workspace = Path(tempfile.mkdtemp(prefix=f"bench-{task.name}-"))

        # Setup: create test data if needed
        if task.name == "read_and_extract":
            (workspace / "test_data.txt").write_text("1\n2\n3\n4\n5\n")

        import os
        original_dir = os.getcwd()
        os.chdir(workspace)

        console.print(f"\n[cyan]Running: {task.name}...[/cyan]")
        result = await run_benchmark_task(task, workspace)
        results.append(result)

        status = "[green]✅ PASS[/green]" if result.passed else "[red]❌ FAIL[/red]"
        console.print(f"  {status} ({result.tokens_used} tokens, {result.elapsed_seconds:.1f}s)")
        if result.error:
            console.print(f"  [red]Error: {result.error}[/red]")

        os.chdir(original_dir)
        shutil.rmtree(workspace, ignore_errors=True)

    return results


def print_results(results: list[BenchmarkResult]) -> None:
    """Print a summary table of benchmark results."""
    table = Table(title=f"Benchmark Results — {DEFAULT_MODEL}", show_lines=True)
    table.add_column("Task", style="bold")
    table.add_column("Status", justify="center")
    table.add_column("Tokens", justify="right")
    table.add_column("Tools", justify="right")
    table.add_column("Time", justify="right")

    for r in results:
        status = "[green]PASS[/green]" if r.passed else "[red]FAIL[/red]"
        table.add_row(r.task_name, status, str(r.tokens_used),
                      str(r.tool_calls), f"{r.elapsed_seconds:.1f}s")

    passed = sum(1 for r in results if r.passed)
    total = len(results)
    total_tokens = sum(r.tokens_used for r in results)

    table.add_row(
        f"[bold]Total: {passed}/{total}[/bold]", "",
        f"[bold]{total_tokens}[/bold]", "",
        f"[bold]{sum(r.elapsed_seconds for r in results):.1f}s[/bold]",
    )

    console.print(table)
    console.print(f"\n[bold]Pass rate: {passed}/{total} ({100*passed/total:.0f}%)[/bold]")


async def main() -> None:
    print_header("Week 8 — Benchmark Suite", f"Model: {DEFAULT_MODEL}")
    validate_setup()

    results = await run_benchmark_suite()
    print_results(results)


if __name__ == "__main__":
    asyncio.run(main())
