"""Offline tests for the Week 1 ReAct loop contract."""

from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parents[1] / "code"
sys.path.insert(0, str(CODE_DIR))

from agent import agent_loop
from shared.models import ModelResponse, ToolCall


class AgentLoopTests(unittest.TestCase):
    def test_approved_tool_result_returns_to_model(self) -> None:
        class Provider:
            def __init__(self) -> None:
                self.calls = 0

            async def chat(self, messages, tools=None):
                self.calls += 1
                if self.calls == 1:
                    return ModelResponse("", [ToolCall("call-1", "read_file", {"path": "README.md"})], {}, {"prompt_tokens": 2, "completion_tokens": 3})
                self.assert_tool_result(messages)
                return ModelResponse("The README was read.", [], {}, {"prompt_tokens": 4, "completion_tokens": 5})

            @staticmethod
            def assert_tool_result(messages):
                assert messages[-1].role == "tool"
                assert messages[-1].content == "README contents"

        history = []
        answer = asyncio.run(agent_loop("Read the README", history, provider_factory=Provider, permission_resolver=lambda *_: True, tool_executor=lambda *_: "README contents"))
        self.assertEqual(answer, "The README was read.")
        self.assertEqual([message.role for message in history], ["user", "assistant", "tool", "assistant"])

    def test_denied_tool_becomes_a_model_observation(self) -> None:
        class Provider:
            def __init__(self) -> None:
                self.calls = 0

            async def chat(self, messages, tools=None):
                self.calls += 1
                if self.calls == 1:
                    return ModelResponse("", [ToolCall("call-1", "write_file", {"path": "x", "content": "x"})], {}, {})
                return ModelResponse("I could not write the file.", [], {}, {})

        executed = False
        def tool_executor(*_):
            nonlocal executed
            executed = True
            return "unexpected"

        answer = asyncio.run(agent_loop("Write x", [], provider_factory=Provider, permission_resolver=lambda *_: False, tool_executor=tool_executor))
        self.assertEqual(answer, "I could not write the file.")
        self.assertFalse(executed)


if __name__ == "__main__":
    unittest.main()
