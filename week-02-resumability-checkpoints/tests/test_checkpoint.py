"""Offline baseline tests for the append-only Week 2 checkpoint format."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parents[1] / "code"
sys.path.insert(0, str(CODE_DIR))

from checkpoint import CheckpointFormatError, CheckpointReader, CheckpointWriter


class CheckpointTests(unittest.TestCase):
    def test_event_log_rebuilds_tool_conversation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            session = Path(directory)
            writer = CheckpointWriter(session)
            writer.log_user_message("Inspect README")
            writer.log_tool_call("read_file", {"path": "README.md"}, "tool-1")
            writer.log_tool_result("read_file", "contents", "tool-1")
            writer.log_step_complete("tool-1")
            writer.log_assistant_response("Done.")
            state = CheckpointReader(session).load()
        self.assertTrue(state.is_complete)
        self.assertEqual(state.completed_steps, {"tool-1"})
        self.assertEqual([message["role"] for message in state.messages], ["user", "assistant", "tool", "assistant"])
        self.assertEqual(state.messages[2]["tool_call_id"], "tool-1")

    def test_empty_session_has_no_checkpoint_and_empty_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            reader = CheckpointReader(Path(directory))
            state = reader.load()
        self.assertFalse(reader.has_checkpoint())
        self.assertEqual(state.messages, [])
        self.assertFalse(state.is_complete)

    def test_dangling_tool_call_is_removed_before_resume(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            session = Path(directory)
            writer = CheckpointWriter(session)
            writer.log_user_message("Inspect README")
            writer.log_tool_call("read_file", {"path": "README.md"}, "done")
            writer.log_tool_result("read_file", "contents", "done")
            writer.log_step_complete("done")
            writer.log_tool_call("bash", {"command": "pytest"}, "crashed")
            state = CheckpointReader(session).load()

        self.assertEqual([message["role"] for message in state.messages], ["user", "assistant", "tool"])
        self.assertEqual(state.completed_steps, {"done"})

    def test_torn_final_record_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            session = Path(directory)
            writer = CheckpointWriter(session)
            writer.log_user_message("Inspect README")
            with (session / "checkpoint.jsonl").open("a", encoding="utf-8") as log:
                log.write('{"event_type":')
            state = CheckpointReader(session).load()

        self.assertEqual(state.messages, [{"role": "user", "content": "Inspect README"}])

    def test_corruption_before_the_final_record_fails_with_line_number(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            session = Path(directory)
            (session / "checkpoint.jsonl").write_text(
                '{"event_type":\n'
                '{"event_type": "user_message", "data": {"message": "hello"}}\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(CheckpointFormatError, "line 1"):
                CheckpointReader(session).load()

    def test_incomplete_event_fails_with_actionable_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            session = Path(directory)
            (session / "checkpoint.jsonl").write_text(
                '{"event_type": "tool_call", "data": {}}\n', encoding="utf-8"
            )
            with self.assertRaisesRegex(CheckpointFormatError, "tool_name"):
                CheckpointReader(session).load()


if __name__ == "__main__":
    unittest.main()
