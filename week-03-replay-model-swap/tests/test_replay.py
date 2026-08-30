"""Offline tests for Week 3 replay artifacts; no model API key is needed."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
import asyncio
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parents[1] / "code"
sys.path.insert(0, str(CODE_DIR))

from comparison_report import markdown_report, run_summary
from replay_core import events_through_step, history_from_events, load_events
import replay_harness
from shared.models import ModelResponse


EVENTS = [
    {"event_type": "user_message", "data": {"message": "Inspect this project"}, "step_id": "user"},
    {"event_type": "tool_call", "data": {"tool_name": "bash", "arguments": {"command": "ls"}}, "step_id": "step-1"},
    {"event_type": "tool_result", "data": {"tool_name": "bash", "result": "README.md"}, "step_id": "step-1"},
    {"event_type": "step_complete", "data": {"completed": True}, "step_id": "step-1"},
    {"event_type": "assistant_response", "data": {"response": "The project has a README."}, "step_id": "answer"},
]


class ReplayCoreTests(unittest.TestCase):
    def test_fork_prefix_stops_after_requested_completed_step(self) -> None:
        prefix = events_through_step(EVENTS, 1)
        self.assertEqual([event["event_type"] for event in prefix], ["user_message", "tool_call", "tool_result", "step_complete"])
        history = history_from_events(prefix)
        self.assertEqual([message.role for message in history], ["user", "assistant", "tool"])

    def test_zero_step_replay_keeps_initial_user_message(self) -> None:
        prefix = events_through_step(EVENTS, 0)
        self.assertEqual(len(prefix), 1)
        self.assertEqual(prefix[0]["event_type"], "user_message")

    def test_missing_step_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "contains 1"):
            events_through_step(EVENTS, 2)

    def test_replay_writes_independent_branch_with_metrics(self) -> None:
        class FakeProvider:
            async def chat(self, messages, tools):
                return ModelResponse("A replayed answer.", [], {}, {"prompt_tokens": 7, "completion_tokens": 3})

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source, branch = root / "source", root / "branch"
            source.mkdir()
            (source / "checkpoint.jsonl").write_text("\n".join(json.dumps(event) for event in EVENTS) + "\n", encoding="utf-8")
            original_factory = replay_harness.get_provider
            replay_harness.get_provider = lambda model: FakeProvider()
            try:
                metrics = asyncio.run(replay_harness.replay_from(source, 1, branch, "fake-model"))
            finally:
                replay_harness.get_provider = original_factory
            branch_events = load_events(branch)
            metrics_file = json.loads((branch / "run_metrics.json").read_text(encoding="utf-8"))
        self.assertEqual(metrics.answer, "A replayed answer.")
        self.assertEqual(metrics_file["total_tokens"], 10)
        self.assertEqual([event["event_type"] for event in branch_events][-2:], ["replay_metadata", "assistant_response"])


class ComparisonReportTests(unittest.TestCase):
    def test_report_includes_metrics_and_answer(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            session = Path(temporary_directory) / "swap-gpt"
            session.mkdir()
            (session / "checkpoint.jsonl").write_text("\n".join(json.dumps(event) for event in EVENTS) + "\n", encoding="utf-8")
            (session / "run_metrics.json").write_text(json.dumps({
                "model": "gpt-4o-mini", "prompt_tokens": 100, "completion_tokens": 20,
                "tool_calls": 1, "elapsed_seconds": 1.25,
            }), encoding="utf-8")
            summary = run_summary(session)
            report = markdown_report([summary])
        self.assertIn("$0.000027", report)
        self.assertIn("The project has a README.", report)

    def test_invalid_checkpoint_json_has_line_number(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            session = Path(temporary_directory)
            (session / "checkpoint.jsonl").write_text("not-json\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "line 1"):
                load_events(session)


if __name__ == "__main__":
    unittest.main()
