"""Offline baseline tests for the append-only Week 2 checkpoint format."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parents[1] / "code"
sys.path.insert(0, str(CODE_DIR))

from checkpoint import CheckpointReader, CheckpointWriter


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


if __name__ == "__main__":
    unittest.main()
