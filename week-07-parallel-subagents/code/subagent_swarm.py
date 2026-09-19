"""Bounded, structured parallel subagents for Week 7.

The coordinator only fans out independent, capped subtasks. Every child returns
one validated report; it never shares its full conversation with a sibling.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from collections.abc import Awaitable, Callable
from dataclasses import replace
from pathlib import Path
from typing import Any, Protocol

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from shared.config import DEFAULT_MODEL, validate_setup
from shared.models import Message, ModelResponse, get_provider
from shared.utils import console, print_header, print_response

from budget_contract import ChildBudget, SubagentReport

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "week-01-bare-agent-loop" / "code"))
MAX_SUBTASKS = 5
ProviderFactory = Callable[[], Any]
ToolExecutor = Callable[[str, dict[str, Any]], str]

EXPLORE_TOOL_SCHEMAS = [
    {"type": "function", "function": {"name": "read_file", "description": "Read one text file within the workspace.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "list_files", "description": "List direct entries in one workspace directory.", "parameters": {"type": "object", "properties": {"path": {"type": "string", "default": "."}}}}},
]


def _workspace_path(path: str) -> Path:
    root = Path.cwd().resolve()
    target = (root / path).resolve()
    if target != root and root not in target.parents:
        raise ValueError("Path escapes workspace")
    return target


def safe_explore_tool(name: str, arguments: dict[str, Any]) -> str:
    """Default child tools are read-only and cannot leave the current workspace."""
    try:
        path = _workspace_path(str(arguments.get("path", ".")))
        if name == "read_file":
            if not path.is_file():
                return f"Error: Not a file: {arguments.get('path')}"
            content = path.read_text(encoding="utf-8", errors="replace")
            return content[:50_000] + ("\n... [truncated]" if len(content) > 50_000 else "")
        if name == "list_files":
            if not path.is_dir():
                return f"Error: Not a directory: {arguments.get('path', '.')}"
            return "\n".join(entry.name for entry in sorted(path.iterdir())) or "(empty directory)"
        return f"Error: Tool '{name}' is not available to read-only exploration children."
    except (OSError, ValueError) as exc:
        return f"Error: {exc}"


def parse_subtasks(text: str, maximum: int = MAX_SUBTASKS) -> list[str]:
    """Parse a model decomposition and cap it before it becomes fan-out."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        parts = cleaned.split("\n", 1)
        cleaned = parts[1].rsplit("```", 1)[0] if len(parts) == 2 and "```" in parts[1] else ""
    try:
        candidate = json.loads(cleaned)
    except json.JSONDecodeError:
        candidate = [line.lstrip("-0123456789. ").strip() for line in cleaned.splitlines()]
    if not isinstance(candidate, list):
        raise ValueError("Task decomposition must be a JSON array or a bullet list")
    subtasks = []
    for item in candidate:
        task = str(item).strip()
        if task and task not in subtasks:
            subtasks.append(task[:500])
    if not subtasks:
        raise ValueError("Task decomposition produced no usable subtasks")
    return subtasks[:maximum]


def facts_from_text(text: str) -> tuple[str, ...]:
    """Extract a bounded list of report facts without trusting free-form length."""
    return tuple(line.lstrip("-• ").strip()[:300] for line in text.splitlines() if line.lstrip().startswith(("-", "•")))[:10]


async def run_child_agent(
    subtask: str,
    agent_id: int,
    budget: ChildBudget = ChildBudget(),
    provider_factory: ProviderFactory = get_provider,
    tool_executor: ToolExecutor = safe_explore_tool,
    attempt: int = 1,
) -> SubagentReport:
    """Run one child in an isolated history with a token, turn, and time budget."""
    started = time.perf_counter()
    tokens_used = tool_calls = 0
    try:
        provider = provider_factory()
        history = [
            Message(role="system", content=(
                f"You are child {agent_id}. Complete only this independent subtask: {subtask}\n"
                "Return a concise factual report. Do not claim work you did not verify."
            )),
            Message(role="user", content=subtask),
        ]
        for _ in range(budget.max_iterations):
            response: ModelResponse = await provider.chat(history, tools=EXPLORE_TOOL_SCHEMAS)
            tokens_used += response.usage.get("prompt_tokens", 0) + response.usage.get("completion_tokens", 0)
            if tokens_used > budget.max_tokens:
                return SubagentReport(subtask, "partial", "Token budget exceeded before completion.", ("Budget exceeded",), tokens_used, tool_calls, time.perf_counter() - started, attempt=attempt)
            if response.tool_calls:
                for call in response.tool_calls:
                    tool_calls += 1
                    result = tool_executor(call.name, call.arguments)
                    history.extend([
                        Message(role="assistant", content="", tool_calls=[{"id": call.id, "name": call.name, "arguments": call.arguments}]),
                        Message(role="tool", content=result, tool_call_id=call.id),
                    ])
                continue
            if response.content:
                return SubagentReport(subtask, "success", response.content[:2_000], facts_from_text(response.content), tokens_used, tool_calls, time.perf_counter() - started, attempt=attempt)
            return SubagentReport(subtask, "partial", "Model returned no tool call or final response.", (), tokens_used, tool_calls, time.perf_counter() - started, attempt=attempt)
        return SubagentReport(subtask, "partial", "Iteration budget reached.", (), tokens_used, tool_calls, time.perf_counter() - started, attempt=attempt)
    except Exception as exc:
        return SubagentReport.failed(subtask, str(exc), time.perf_counter() - started, attempt)


async def bounded_child(
    subtask: str, agent_id: int, semaphore: asyncio.Semaphore, budget: ChildBudget,
    provider_factory: ProviderFactory, tool_executor: ToolExecutor,
) -> SubagentReport:
    """Ensure one failed or slow child cannot starve the rest of the swarm."""
    async with semaphore:
        try:
            return await asyncio.wait_for(run_child_agent(subtask, agent_id, budget, provider_factory, tool_executor), timeout=budget.timeout_seconds)
        except TimeoutError:
            return SubagentReport.failed(subtask, f"Timed out after {budget.timeout_seconds:.0f}s", budget.timeout_seconds)


async def run_children(
    subtasks: list[str], budget: ChildBudget = ChildBudget(), max_concurrency: int = 3,
    provider_factory: ProviderFactory = get_provider, tool_executor: ToolExecutor = safe_explore_tool,
    retry_failed: bool = True,
) -> list[SubagentReport]:
    """Fan out bounded work, then retry only failed children once."""
    if not 1 <= max_concurrency <= MAX_SUBTASKS:
        raise ValueError(f"max_concurrency must be between 1 and {MAX_SUBTASKS}")
    semaphore = asyncio.Semaphore(max_concurrency)
    reports = await asyncio.gather(*[
        bounded_child(subtask, index + 1, semaphore, budget, provider_factory, tool_executor)
        for index, subtask in enumerate(subtasks[:MAX_SUBTASKS])
    ])
    if retry_failed:
        retry_budget = replace(budget, max_tokens=budget.max_tokens * 2)
        for index, report in enumerate(reports):
            if report.status == "failed":
                reports[index] = await bounded_child(report.subtask, index + 1, semaphore, retry_budget, provider_factory, tool_executor)
                reports[index] = replace(reports[index], attempt=2)
    return reports


async def decompose_task(task: str, provider_factory: ProviderFactory = get_provider) -> list[str]:
    """Ask the coordinator model for independent work items, then validate them."""
    provider = provider_factory()
    response = await provider.chat([
        Message(role="system", content=(
            "Break the task into at most five independent, read-only subtasks. "
            "Return only a JSON array of strings; do not include dependent implementation steps."
        )),
        Message(role="user", content=task),
    ])
    return parse_subtasks(response.content)


async def merge_reports(task: str, reports: list[SubagentReport], provider_factory: ProviderFactory = get_provider) -> str:
    """Merge bounded report fields; failed reports remain visible to the reviewer."""
    evidence = "\n\n".join(
        f"Subtask: {report.subtask}\nStatus: {report.status}\nSummary: {report.summary}\n"
        f"Facts: {'; '.join(report.key_facts)}\nError: {report.error or 'none'}"
        for report in reports
    )
    response = await provider_factory().chat([
        Message(role="system", content="Synthesize the reports into a concise answer. State gaps or failed subtasks explicitly."),
        Message(role="user", content=f"Original task: {task}\n\nReports:\n{evidence}"),
    ])
    return response.content or "No final synthesis was returned."


async def run_swarm(task: str, budget: ChildBudget = ChildBudget(), max_concurrency: int = 3) -> tuple[str, list[SubagentReport]]:
    """Run coordinator → bounded fan-out → evidence-preserving merge."""
    subtasks = await decompose_task(task)
    console.print(f"[bold]Decomposed into {len(subtasks)} independent subtasks.[/bold]")
    reports = await run_children(subtasks, budget, max_concurrency)
    answer = await merge_reports(task, reports)
    return answer, reports


async def main() -> None:
    parser = argparse.ArgumentParser(description="Week 7 bounded parallel subagent swarm")
    parser.add_argument("--task", default="Inspect this project: identify Python files, documentation, dependencies, and tests.")
    parser.add_argument("--max-concurrency", type=int, default=3)
    parser.add_argument("--child-token-budget", type=int, default=8_000)
    args = parser.parse_args()
    print_header("Week 7 — Parallel Subagents", f"Model: {DEFAULT_MODEL} | Bounded fan-out")
    validate_setup()
    answer, reports = await run_swarm(args.task, ChildBudget(max_tokens=args.child_token_budget), args.max_concurrency)
    print_response(answer)
    for index, report in enumerate(reports, start=1):
        console.print(f"Child {index}: {report.status}, {report.tokens_used} tokens, {report.elapsed_seconds:.1f}s, attempt {report.attempt}")


if __name__ == "__main__":
    asyncio.run(main())
