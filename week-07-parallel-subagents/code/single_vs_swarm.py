"""Compare sequential and parallel execution with the same child contract."""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from budget_contract import SubagentReport


Worker = Callable[[str, int], Awaitable[SubagentReport]]


@dataclass(frozen=True)
class ExecutionResult:
    strategy: str
    elapsed_seconds: float
    total_tokens: int
    successful_children: int


async def compare_execution(subtasks: list[str], worker: Worker) -> tuple[ExecutionResult, ExecutionResult]:
    """Execute identical work sequentially and in parallel for an honest timing comparison."""
    started = time.perf_counter()
    sequential_reports = [await worker(subtask, index) for index, subtask in enumerate(subtasks, start=1)]
    sequential = ExecutionResult("single agent (sequential)", time.perf_counter() - started, sum(report.tokens_used for report in sequential_reports), sum(report.status == "success" for report in sequential_reports))

    started = time.perf_counter()
    swarm_reports = await asyncio.gather(*(worker(subtask, index) for index, subtask in enumerate(subtasks, start=1)))
    swarm = ExecutionResult("swarm (parallel)", time.perf_counter() - started, sum(report.tokens_used for report in swarm_reports), sum(report.status == "success" for report in swarm_reports))
    return sequential, swarm


async def offline_worker(subtask: str, agent_id: int) -> SubagentReport:
    """Deterministic stand-in that demonstrates scheduling, not model quality."""
    await asyncio.sleep(0.03)
    return SubagentReport(subtask, "success", f"Child {agent_id} completed its independent review.", ("Review completed",), 100, 1, 0.03)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Offline sequential-versus-swarm scheduling comparison")
    parser.add_argument("--children", type=int, default=4)
    args = parser.parse_args()
    if not 1 <= args.children <= 10:
        parser.error("children must be between 1 and 10")
    results = await compare_execution([f"Independent review {index}" for index in range(1, args.children + 1)], offline_worker)
    print("Week 7 — Single Agent vs Swarm (offline scheduling demo)\n")
    for result in results:
        print(f"{result.strategy}: {result.elapsed_seconds:.3f}s | {result.total_tokens} tokens | {result.successful_children} successful children")
    print("\nBoth strategies use the same deterministic worker. Live-model quality requires task-specific evaluation.")


if __name__ == "__main__":
    asyncio.run(main())
