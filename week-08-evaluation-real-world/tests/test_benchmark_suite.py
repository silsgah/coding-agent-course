"""Offline safety and behavior tests for Week 8 benchmarks."""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import unittest
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parents[1] / "code"
sys.path.insert(0, str(CODE_DIR))

from benchmark_suite import BenchmarkTask, WorkspaceExecutor, run_benchmark_suite, run_benchmark_task, write_results
from github_issue_agent import plan_issue
from shared.models import ModelResponse, ToolCall


class BenchmarkSafetyTests(unittest.TestCase):
    def test_task_requires_callable_validator(self) -> None:
        with self.assertRaises(TypeError):
            BenchmarkTask("unsafe", "prompt", "result == 'pass'")  # type: ignore[arg-type]

    def test_executor_is_workspace_scoped(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            executor = WorkspaceExecutor(workspace)
            self.assertIn("Written", executor.execute("write_file", {"path": "nested/a.txt", "content": "safe"}))
            self.assertEqual(executor.execute("read_file", {"path": "nested/a.txt"}), "safe")
            self.assertIn("escapes benchmark workspace", executor.execute("write_file", {"path": "../escape.txt", "content": "no"}))

    def test_benchmark_runs_tool_loop_without_changing_process_cwd(self) -> None:
        class Provider:
            def __init__(self) -> None:
                self.calls = 0

            async def chat(self, messages, tools=None):
                self.calls += 1
                if self.calls == 1:
                    return ModelResponse("", [ToolCall("write", "write_file", {"path": "hello.txt", "content": "hello"})], {}, {"prompt_tokens": 2, "completion_tokens": 3})
                return ModelResponse("Done", [], {}, {"prompt_tokens": 4, "completion_tokens": 5})

        task = BenchmarkTask("write", "Write hello.txt", lambda workspace, answer: (workspace / "hello.txt").read_text() == "hello")
        original_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as directory:
            result = asyncio.run(run_benchmark_task(task, Path(directory), Provider))
        self.assertTrue(result.passed)
        self.assertEqual(result.tokens_used, 14)
        self.assertEqual(os.getcwd(), original_cwd)

    def test_suite_isolates_fixtures_and_writes_json(self) -> None:
        class Provider:
            async def chat(self, messages, tools=None):
                return ModelResponse("There are 1 files.", [], {}, {"prompt_tokens": 1, "completion_tokens": 1})

        task = BenchmarkTask("one", "Count files", lambda workspace, answer: "1" in answer)
        results = asyncio.run(run_benchmark_suite([task], Provider))
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "results.json"
            write_results(results, output)
            self.assertIn('"task_name": "one"', output.read_text(encoding="utf-8"))
        self.assertTrue(results[0].passed)

    def test_issue_plan_has_no_external_effects_and_requires_review(self) -> None:
        packet = plan_issue(" Add validation to the CLI ")
        self.assertEqual(packet["status"], "requires_human_approval")
        self.assertIn("does not call GitHub", packet["external_effects"])
        with self.assertRaises(ValueError):
            plan_issue("   ")


if __name__ == "__main__":
    unittest.main()
