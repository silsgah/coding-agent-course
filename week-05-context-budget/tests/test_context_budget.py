"""Offline tests for Week 5 context and memory examples."""

from __future__ import annotations

import asyncio
import sys
import tempfile
import unittest
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parents[1] / "code"
sys.path.insert(0, str(CODE_DIR))

from context_budget import ContextBudget, compact_history
from lsp_context import find_symbol_source
from memory_strategies import AgentsMemory, LearnedMemory, SkillsManager, create_demo_skills
from nooa_comparison import compare_strategies
from shared.models import Message, ModelResponse


class ContextBudgetTests(unittest.TestCase):
    def test_budget_reserves_response_capacity(self) -> None:
        budget = ContextBudget(max_tokens=100, reserved_for_response=20, system_tokens=10, memory_tokens=15, history_tokens=25)
        self.assertEqual(budget.used_tokens, 50)
        self.assertEqual(budget.available_tokens, 30)
        self.assertFalse(budget.needs_compaction)

    def test_invalid_budget_configuration_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            ContextBudget(max_tokens=0)
        with self.assertRaises(ValueError):
            ContextBudget(compaction_threshold=1.1)

    def test_compaction_preserves_system_and_recent_messages(self) -> None:
        class FakeProvider:
            async def chat(self, messages):
                return ModelResponse("Key decisions and paths.", [], {}, {})

        messages = [Message(role="system", content="system")] + [Message(role="user", content=f"message {index}") for index in range(6)]
        compacted = asyncio.run(compact_history(messages, FakeProvider(), keep_recent=2))
        self.assertEqual(compacted[0].content, "system")
        self.assertIn("Previous conversation summary", compacted[1].content)
        self.assertEqual([message.content for message in compacted[-2:]], ["message 4", "message 5"])

    def test_method_boundary_has_no_more_prompt_load_than_growing_history(self) -> None:
        growing, method = compare_strategies(["inspect", "edit", "test"], 4_000, 16_000, 0.8)
        self.assertLessEqual(method.input_tokens, growing.input_tokens)
        self.assertEqual(method.compactions, 0)


class MemoryAndSymbolTests(unittest.TestCase):
    def test_memory_and_skills_are_project_scoped(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "AGENTS.md").write_text("# Local instructions\nUse pytest.\n", encoding="utf-8")
            self.assertIn("Use pytest", AgentsMemory(root).load())
            memory = LearnedMemory(root)
            memory.append("The project uses a src layout.")
            self.assertIn("src layout", memory.load())
            create_demo_skills(root / ".agent" / "skills")
            skills = SkillsManager(root / ".agent" / "skills")
            self.assertIn("python-best-practices", skills.list_skills())

    def test_symbol_reader_returns_only_requested_definition(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "example.py"
            path.write_text("def first():\n    return 1\n\nclass Target:\n    pass\n", encoding="utf-8")
            self.assertEqual(find_symbol_source(path, "Target"), "class Target:\n    pass\n")
            with self.assertRaises(ValueError):
                find_symbol_source(path, "missing")


if __name__ == "__main__":
    unittest.main()
