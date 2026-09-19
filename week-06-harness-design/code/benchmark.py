"""Repeatable offline smoke benchmark for the Week 6 object harness.

It validates a known tool-call trajectory using a scripted provider. Live model
quality belongs in a separate, provider-backed evaluation suite.
"""

from __future__ import annotations

import asyncio
import tempfile
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from agent_as_object import CodingAgent
from shared.models import ModelResponse, ToolCall


class ScriptedProvider:
    """Provider double that returns one tool call followed by a final answer."""

    def __init__(self) -> None:
        self.calls = 0

    async def chat(self, messages, tools=None) -> ModelResponse:
        self.calls += 1
        if self.calls == 1:
            return ModelResponse("", [ToolCall("call-1", "list_files", {"path": "."})], {}, {"prompt_tokens": 20, "completion_tokens": 5})
        return ModelResponse("The workspace contains README.md.", [], {}, {"prompt_tokens": 30, "completion_tokens": 10})


@dataclass(frozen=True)
class BenchmarkResult:
    passed: bool
    tool_calls: int
    total_tokens: int
    answer: str


async def run_smoke_benchmark() -> BenchmarkResult:
    """Exercise provider→method→tool-result→final-answer integration offline."""
    with tempfile.TemporaryDirectory(prefix="week6-benchmark-") as directory:
        workspace = Path(directory)
        (workspace / "README.md").write_text("# Fixture\n", encoding="utf-8")
        agent = CodingAgent(work_dir=workspace, provider=ScriptedProvider())
        answer = await agent.run("List the files, then summarize them.")
        stats = agent.stats()
    return BenchmarkResult("README.md" in answer and stats.tool_calls == 1, stats.tool_calls, stats.total_tokens, answer)


def main() -> None:
    result = asyncio.run(run_smoke_benchmark())
    print("Week 6 — Offline Smoke Benchmark")
    print(f"Passed: {result.passed}\nTool calls: {result.tool_calls}\nTotal tokens: {result.total_tokens}\nAnswer: {result.answer}")
    raise SystemExit(0 if result.passed else 1)


if __name__ == "__main__":
    main()
