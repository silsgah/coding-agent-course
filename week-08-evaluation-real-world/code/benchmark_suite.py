"""Safe, repeatable benchmark primitives for Week 8.

Validators are Python callables chosen by the harness, never model-provided
strings evaluated at runtime. Each benchmark owns a temporary workspace and a
scoped executor; the runner never changes the process working directory.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import tempfile
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from shared.config import DEFAULT_MODEL, validate_setup
from shared.models import Message, ModelResponse, get_provider
from shared.utils import console, print_header


Validator = Callable[[Path, str], bool]
Setup = Callable[[Path], None]
ProviderFactory = Callable[[], Any]

TOOL_SCHEMAS = [
    {"type": "function", "function": {"name": "read_file", "description": "Read one UTF-8 text file in the benchmark workspace.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "write_file", "description": "Write one UTF-8 text file in the benchmark workspace.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}}},
    {"type": "function", "function": {"name": "list_files", "description": "List direct entries in a benchmark workspace directory.", "parameters": {"type": "object", "properties": {"path": {"type": "string", "default": "."}}}}},
]


def workspace_path(workspace: Path, path: str) -> Path:
    """Resolve a benchmark path and reject escapes through paths or symlinks."""
    root = workspace.resolve()
    target = (root / path).resolve()
    if target != root and root not in target.parents:
        raise ValueError("Path escapes benchmark workspace")
    return target


class WorkspaceExecutor:
    """Minimal deterministic tool surface for benchmark fixtures."""

    def __init__(self, workspace: Path):
        self.workspace = workspace.resolve()

    def execute(self, name: str, arguments: dict[str, Any]) -> str:
        try:
            path = workspace_path(self.workspace, str(arguments.get("path", ".")))
            if name == "read_file":
                if not path.is_file():
                    return f"Error: File not found: {arguments.get('path')}"
                return path.read_text(encoding="utf-8", errors="replace")[:50_000]
            if name == "write_file":
                path.parent.mkdir(parents=True, exist_ok=True)
                content = str(arguments.get("content", ""))
                path.write_text(content, encoding="utf-8")
                return f"Written {len(content)} characters to {path.relative_to(self.workspace)}"
            if name == "list_files":
                if not path.is_dir():
                    return f"Error: Directory not found: {arguments.get('path', '.')}"
                return "\n".join(entry.name for entry in sorted(path.iterdir())) or "(empty directory)"
            return f"Error: Unknown benchmark tool: {name}"
        except (OSError, ValueError) as exc:
            return f"Error: {exc}"


@dataclass(frozen=True)
class BenchmarkTask:
    name: str
    prompt: str
    validator: Validator
    category: str = "general"
    max_tokens: int = 10_000
    max_iterations: int = 8
    setup: Setup | None = None

    def __post_init__(self) -> None:
        if not callable(self.validator):
            raise TypeError("Benchmark validators must be trusted callables")
        if self.max_tokens <= 0 or self.max_iterations <= 0:
            raise ValueError("Benchmark budgets must be positive")


@dataclass(frozen=True)
class BenchmarkResult:
    task_name: str
    passed: bool
    score: float
    tokens_used: int
    tool_calls: int
    elapsed_seconds: float
    error: str | None = None
    agent_answer: str = ""


def contains_greet(workspace: Path, _: str) -> bool:
    path = workspace / "hello.py"
    return path.is_file() and "def greet" in path.read_text(encoding="utf-8")


def contains_number(_: Path, answer: str) -> bool:
    return any(character.isdigit() for character in answer)


def reports_total(_: Path, answer: str) -> bool:
    return "15" in answer


def creates_output_files(workspace: Path, _: str) -> bool:
    return all((workspace / "output" / name).is_file() for name in ("a.txt", "b.txt", "c.txt"))


def reports_missing_file(_: Path, answer: str) -> bool:
    return any(word in answer.lower() for word in ("not", "error", "exist"))


def setup_number_fixture(workspace: Path) -> None:
    (workspace / "test_data.txt").write_text("1\n2\n3\n4\n5\n", encoding="utf-8")


BENCHMARK_TASKS = [
    BenchmarkTask("create_file", "Create hello.py with a greet(name) function that returns a greeting.", contains_greet, "file_creation"),
    BenchmarkTask("list_and_summarize", "List all files in the current directory and say how many there are.", contains_number, "exploration"),
    BenchmarkTask("read_and_extract", "Read test_data.txt and report the total of its numbers.", reports_total, "analysis", setup=setup_number_fixture),
    BenchmarkTask("multi_step", "Create output/a.txt, output/b.txt, and output/c.txt, each containing its filename.", creates_output_files, "multi_step"),
    BenchmarkTask("error_handling", "Try to read nonexistent_file_xyz.txt and gracefully report that it does not exist.", reports_missing_file, "error_handling"),
]


async def run_benchmark_task(task: BenchmarkTask, workspace: Path, provider_factory: ProviderFactory = get_provider) -> BenchmarkResult:
    """Run one task in its supplied workspace and validate via a trusted callable."""
    started = time.perf_counter()
    tokens_used = tool_calls = 0
    executor = WorkspaceExecutor(workspace)
    try:
        provider = provider_factory()
        history = [Message(role="system", content="You are a coding assistant. Complete the task using only the supplied tools."), Message(role="user", content=task.prompt)]
        for _ in range(task.max_iterations):
            response: ModelResponse = await provider.chat(history, tools=TOOL_SCHEMAS)
            tokens_used += response.usage.get("prompt_tokens", 0) + response.usage.get("completion_tokens", 0)
            if tokens_used > task.max_tokens:
                return BenchmarkResult(task.name, False, 0.0, tokens_used, tool_calls, time.perf_counter() - started, "Token budget exceeded")
            if response.tool_calls:
                for call in response.tool_calls:
                    tool_calls += 1
                    result = executor.execute(call.name, call.arguments)
                    history.extend([Message(role="assistant", content="", tool_calls=[{"id": call.id, "name": call.name, "arguments": call.arguments}]), Message(role="tool", content=result, tool_call_id=call.id)])
                continue
            if response.content:
                passed = bool(task.validator(workspace, response.content))
                return BenchmarkResult(task.name, passed, float(passed), tokens_used, tool_calls, time.perf_counter() - started, agent_answer=response.content[:500])
            return BenchmarkResult(task.name, False, 0.0, tokens_used, tool_calls, time.perf_counter() - started, "Model returned no tool call or answer")
        return BenchmarkResult(task.name, False, 0.0, tokens_used, tool_calls, time.perf_counter() - started, "Iteration budget exceeded")
    except Exception as exc:
        return BenchmarkResult(task.name, False, 0.0, tokens_used, tool_calls, time.perf_counter() - started, str(exc))


async def run_benchmark_suite(tasks: list[BenchmarkTask] | None = None, provider_factory: ProviderFactory = get_provider) -> list[BenchmarkResult]:
    """Run each task in an isolated temporary workspace without changing CWD."""
    results = []
    for task in tasks or BENCHMARK_TASKS:
        with tempfile.TemporaryDirectory(prefix=f"bench-{task.name}-") as directory:
            workspace = Path(directory)
            if task.setup:
                task.setup(workspace)
            result = await run_benchmark_task(task, workspace, provider_factory)
            results.append(result)
    return results


def write_results(results: list[BenchmarkResult], output: Path) -> None:
    """Write machine-readable benchmark results for regression comparison."""
    output.write_text(json.dumps([asdict(result) for result in results], indent=2) + "\n", encoding="utf-8")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run isolated Week 8 benchmark tasks")
    parser.add_argument("--json-out", type=Path, help="Optional JSON results file")
    args = parser.parse_args()
    print_header("Week 8 — Benchmark Suite", f"Model: {DEFAULT_MODEL}")
    validate_setup()
    results = await run_benchmark_suite()
    for result in results:
        print(f"{'PASS' if result.passed else 'FAIL'} {result.task_name}: {result.tokens_used} tokens, {result.elapsed_seconds:.2f}s")
    if args.json_out:
        write_results(results, args.json_out)
        console.print(f"[green]Results written to {args.json_out}[/green]")


if __name__ == "__main__":
    asyncio.run(main())
