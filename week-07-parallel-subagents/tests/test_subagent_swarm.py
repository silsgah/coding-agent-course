"""Offline tests for bounded fan-out and the child report contract."""

from __future__ import annotations

import asyncio
import json
import sys
import time
import unittest
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parents[1] / "code"
sys.path.insert(0, str(CODE_DIR))

from budget_contract import ChildBudget, SubagentReport
from single_vs_swarm import compare_execution, offline_worker
from subagent_swarm import MAX_SUBTASKS, parse_subtasks, run_child_agent, run_children, safe_explore_tool
from shared.models import ModelResponse, ToolCall


class SubagentContractTests(unittest.TestCase):
    def test_contract_rejects_invalid_status_and_limits(self) -> None:
        with self.assertRaises(ValueError):
            ChildBudget(max_tokens=0)
        with self.assertRaises(ValueError):
            SubagentReport("task", "unknown", "summary")
        with self.assertRaises(ValueError):
            SubagentReport("task", "success", "x" * 2_001)

    def test_decomposition_is_sanitized_deduplicated_and_capped(self) -> None:
        result = parse_subtasks(json.dumps(["Read README", "Read README", "", *[f"Task {number}" for number in range(10)]]))
        self.assertEqual(result[0], "Read README")
        self.assertEqual(len(result), MAX_SUBTASKS)
        self.assertEqual(parse_subtasks("```json\n[\"One\", \"Two\"]\n```"), ["One", "Two"])

    def test_default_exploration_tools_reject_writes_and_workspace_escapes(self) -> None:
        self.assertIn("not available", safe_explore_tool("write_file", {"path": "x", "content": "x"}))
        self.assertIn("escapes workspace", safe_explore_tool("read_file", {"path": "../outside"}))

    def test_child_tool_loop_returns_structured_success(self) -> None:
        class Provider:
            def __init__(self) -> None:
                self.turn = 0

            async def chat(self, messages, tools=None):
                self.turn += 1
                if self.turn == 1:
                    return ModelResponse("", [ToolCall("call", "read_file", {"path": "x"})], {}, {"prompt_tokens": 10, "completion_tokens": 5})
                return ModelResponse("Found evidence.\n- fact one", [], {}, {"prompt_tokens": 10, "completion_tokens": 5})

        executed: list[tuple[str, dict]] = []
        report = asyncio.run(run_child_agent("Inspect x", 1, ChildBudget(max_tokens=100), provider_factory=Provider, tool_executor=lambda name, args: executed.append((name, args)) or "contents"))
        self.assertEqual(report.status, "success")
        self.assertEqual(report.key_facts, ("fact one",))
        self.assertEqual(executed, [("read_file", {"path": "x"})])

    def test_failed_child_retries_once(self) -> None:
        calls = 0

        class FailingThenWorkingProvider:
            async def chat(self, messages, tools=None):
                nonlocal calls
                calls += 1
                if calls == 1:
                    raise RuntimeError("temporary provider failure")
                return ModelResponse("Recovered.", [], {}, {"prompt_tokens": 1, "completion_tokens": 1})

        reports = asyncio.run(run_children(["Inspect README"], provider_factory=FailingThenWorkingProvider))
        self.assertEqual(reports[0].status, "success")
        self.assertEqual(reports[0].attempt, 2)

    def test_parallel_strategy_reduces_wall_clock_for_independent_work(self) -> None:
        sequential, swarm = asyncio.run(compare_execution(["one", "two", "three"], offline_worker))
        self.assertLess(swarm.elapsed_seconds, sequential.elapsed_seconds)
        self.assertEqual(swarm.total_tokens, sequential.total_tokens)


if __name__ == "__main__":
    unittest.main()
