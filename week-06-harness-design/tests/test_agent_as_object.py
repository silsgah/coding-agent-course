"""Offline contract tests for the Week 6 agent-as-object harness."""

from __future__ import annotations

import asyncio
import tempfile
import sys
import unittest
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parents[1] / "code"
sys.path.insert(0, str(CODE_DIR))

from agent_as_object import CodingAgent, tool
from benchmark import run_smoke_benchmark
from refactor_demo import comparison
from shared.models import ModelResponse, ToolCall


class AgentObjectTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temporary_directory.name)
        (self.workspace / "readme.txt").write_text("hello", encoding="utf-8")
        self.agent = CodingAgent(work_dir=self.workspace, provider=object())

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_schemas_are_derived_from_decorated_methods(self) -> None:
        class ExtendedAgent(CodingAgent):
            @tool
            def count(self, value: int, verbose: bool = False) -> str:
                """Count a value for demonstration."""
                return str(value)

        agent = ExtendedAgent(work_dir=self.workspace, provider=object())
        schema = next(item["function"] for item in agent.tool_schemas() if item["function"]["name"] == "count")
        self.assertEqual(schema["description"], "Count a value for demonstration.")
        self.assertEqual(schema["parameters"]["properties"]["value"]["type"], "integer")
        self.assertEqual(schema["parameters"]["properties"]["verbose"]["default"], False)

    def test_file_tools_cannot_escape_workspace(self) -> None:
        self.assertEqual(self.agent.read_file("readme.txt"), "hello")
        self.assertIn("escapes workspace", self.agent.read_file("../outside.txt"))
        self.assertIn("escapes workspace", self.agent.write_file("../outside.txt", "nope"))
        self.assertFalse((self.workspace.parent / "outside.txt").exists())

    def test_command_policy_blocks_shell_composition_and_destructive_programs(self) -> None:
        self.assertIn("hello", self.agent.bash("echo hello"))
        self.assertIn("Shell operators", self.agent.bash("echo hello | cat"))
        self.assertIn("blocked", self.agent.bash("rm readme.txt"))
        self.assertIn("blocked", self.agent.bash("git clean"))

    def test_unknown_or_invalid_tools_are_controlled_errors(self) -> None:
        self.assertIn("Unknown tool", self.agent.execute_tool("missing", {}))
        self.assertIn("missing a required argument", self.agent.execute_tool("read_file", {}))

    def test_agent_loop_records_tool_and_final_response(self) -> None:
        class Provider:
            def __init__(self) -> None:
                self.calls = 0

            async def chat(self, messages, tools=None):
                self.calls += 1
                if self.calls == 1:
                    return ModelResponse("", [ToolCall("one", "read_file", {"path": "readme.txt"})], {}, {"prompt_tokens": 2, "completion_tokens": 3})
                return ModelResponse("Done.", [], {}, {"prompt_tokens": 4, "completion_tokens": 5})

        agent = CodingAgent(work_dir=self.workspace, provider=Provider())
        self.assertEqual(asyncio.run(agent.run("Read the file.")), "Done.")
        self.assertEqual(agent.stats().tool_calls, 1)
        self.assertEqual(agent.stats().total_tokens, 14)


class WeekSixUtilitiesTests(unittest.TestCase):
    def test_refactor_comparison_and_offline_benchmark(self) -> None:
        report = comparison()
        self.assertEqual(report["week6_tool_count"], 4)
        self.assertTrue(asyncio.run(run_smoke_benchmark()).passed)


if __name__ == "__main__":
    unittest.main()
