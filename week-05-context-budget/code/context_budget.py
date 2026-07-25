"""
Week 5 — Context Budget Manager
=================================

Treat the context window as a finite resource.
Track usage, trigger compaction, and visualize the budget.

Key insight from DecodingAI: compaction fires at ~80% of the
window, not at the limit — leave headroom for the model to think.

Key insight from NOOA: method boundaries are natural compaction
points that avoid mid-conversation summarization entirely.
"""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from shared.config import validate_setup, DEFAULT_MODEL
from shared.models import get_provider, Message
from shared.utils import print_header, print_response, print_tool_call, console

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "week-01-bare-agent-loop" / "code"))
from tools import TOOL_SCHEMAS, execute_tool

from rich.progress import Progress, BarColumn, TextColumn
from rich.panel import Panel


# ---------------------------------------------------------------------------
# Token estimation (rough — real implementations use tiktoken)
# ---------------------------------------------------------------------------
def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token for English."""
    return max(1, len(text) // 4)


def estimate_message_tokens(msg: Message) -> int:
    """Estimate tokens for a single message."""
    tokens = estimate_tokens(msg.content)
    if msg.tool_calls:
        for tc in msg.tool_calls:
            tokens += estimate_tokens(str(tc))
    return tokens + 4  # Message overhead


# ---------------------------------------------------------------------------
# Context Budget Manager
# ---------------------------------------------------------------------------
@dataclass
class ContextBudget:
    """Track and manage context window usage."""

    max_tokens: int = 128_000        # Model's context window
    compaction_threshold: float = 0.8  # Compact at 80%
    reserved_for_response: int = 4_000  # Leave room for the model's answer

    # Tracking
    system_tokens: int = 0
    memory_tokens: int = 0
    history_tokens: int = 0
    compaction_events: int = 0

    @property
    def used_tokens(self) -> int:
        return self.system_tokens + self.memory_tokens + self.history_tokens

    @property
    def available_tokens(self) -> int:
        return self.max_tokens - self.used_tokens - self.reserved_for_response

    @property
    def usage_pct(self) -> float:
        return self.used_tokens / self.max_tokens

    @property
    def needs_compaction(self) -> bool:
        return self.usage_pct >= self.compaction_threshold

    def update_history(self, messages: list[Message]) -> None:
        """Recalculate history token count."""
        self.history_tokens = sum(estimate_message_tokens(m) for m in messages)

    def print_gauge(self) -> None:
        """Print a visual context budget gauge."""
        pct = self.usage_pct * 100
        color = "green" if pct < 60 else "yellow" if pct < 80 else "red"

        bar = "█" * int(pct / 2) + "░" * (50 - int(pct / 2))
        console.print(
            f"\n[{color}]Context: [{bar}] {pct:.0f}%[/{color}]  "
            f"[dim]({self.used_tokens:,}/{self.max_tokens:,} tokens | "
            f"system: {self.system_tokens:,}, memory: {self.memory_tokens:,}, "
            f"history: {self.history_tokens:,})[/dim]"
        )

        if self.needs_compaction:
            console.print("[red bold]⚠️  Context budget exceeded threshold — compaction needed![/red bold]")


# ---------------------------------------------------------------------------
# Compaction — summarize older messages
# ---------------------------------------------------------------------------
async def compact_history(
    messages: list[Message],
    provider: Any,
    keep_recent: int = 4,
) -> list[Message]:
    """
    Compact conversation history by summarizing older messages.

    Keeps the most recent `keep_recent` messages intact and
    summarizes everything before them into a single message.
    """
    if len(messages) <= keep_recent + 1:  # +1 for system prompt
        return messages

    # Split: old messages to summarize, recent messages to keep
    old_messages = messages[1:-keep_recent]  # Skip system prompt
    recent_messages = messages[-keep_recent:]

    if not old_messages:
        return messages

    # Build a summary prompt
    old_text = "\n".join(
        f"[{m.role}]: {m.content[:200]}" for m in old_messages if m.content
    )

    summary_prompt = [
        Message(role="system", content="Summarize the following conversation concisely, "
                "preserving key facts, decisions, and file paths mentioned."),
        Message(role="user", content=f"Conversation to summarize:\n\n{old_text}"),
    ]

    response = await provider.chat(summary_prompt)
    summary = response.content

    console.print(f"\n[yellow]📦 Compacted {len(old_messages)} messages → 1 summary "
                  f"({estimate_tokens(summary)} tokens)[/yellow]")

    # Rebuild: system prompt + summary + recent messages
    return [
        messages[0],  # System prompt
        Message(role="assistant", content=f"[Previous conversation summary]\n{summary}"),
        *recent_messages,
    ]


# ---------------------------------------------------------------------------
# Agent loop with context budget
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """\
You are a helpful coding assistant. You can read files, write files, and run
shell commands. Be thorough but concise — context space is limited.
"""


async def main() -> None:
    print_header(
        "Week 5 — Context Budget",
        f"Model: {DEFAULT_MODEL} | Compaction at 80% | Type 'quit' to exit",
    )
    validate_setup()

    provider = get_provider()
    budget = ContextBudget()
    budget.system_tokens = estimate_tokens(SYSTEM_PROMPT)

    history: list[Message] = [Message(role="system", content=SYSTEM_PROMPT)]

    while True:
        budget.print_gauge()

        try:
            user_input = console.input("\n[bold cyan]You:[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input or user_input.lower() in ("quit", "exit", "q"):
            break

        history.append(Message(role="user", content=user_input))
        budget.update_history(history[1:])

        # Check if compaction is needed BEFORE sending to model
        if budget.needs_compaction:
            console.print("\n[yellow]🔄 Compacting history...[/yellow]")
            history = await compact_history(history, provider)
            budget.update_history(history[1:])
            budget.compaction_events += 1

        for iteration in range(10):
            response = await provider.chat(history, tools=TOOL_SCHEMAS)

            if response.tool_calls:
                for tc in response.tool_calls:
                    print_tool_call(tc.name, tc.arguments)
                    result = execute_tool(tc.name, tc.arguments)

                    history.append(Message(
                        role="assistant", content="",
                        tool_calls=[{"id": tc.id, "name": tc.name, "arguments": tc.arguments}],
                    ))
                    history.append(Message(role="tool", content=result, tool_call_id=tc.id))
                    budget.update_history(history[1:])

                    # Check again after tool results (they can be large)
                    if budget.needs_compaction:
                        history = await compact_history(history, provider)
                        budget.update_history(history[1:])
                        budget.compaction_events += 1
                continue

            if response.content:
                history.append(Message(role="assistant", content=response.content))
                budget.update_history(history[1:])
                print_response(response.content)
                break

    console.print(f"\n[dim]📊 Session stats: {budget.compaction_events} compaction events[/dim]")


if __name__ == "__main__":
    asyncio.run(main())
