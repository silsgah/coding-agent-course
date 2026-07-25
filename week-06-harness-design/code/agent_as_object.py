"""
Week 6 — Agent as Python Object
=================================

Demonstrates the NOOA mental model: an agent is a Python object.
Methods are tools. Fields are state. Docstrings are prompts.

This file shows what a coding agent looks like when built
using the agent-as-object pattern instead of the traditional
loop + tools + schemas approach from Week 1.

Inspired by NVIDIA's NOOA framework (labs-OO-Agents).
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from shared.config import validate_setup, DEFAULT_MODEL
from shared.models import get_provider, Message
from shared.utils import print_header, print_response, console


# ---------------------------------------------------------------------------
# The agent-as-object pattern
# ---------------------------------------------------------------------------
class CodingAgent:
    """
    You are a helpful coding assistant. You can read files, write files,
    and run shell commands to help the user with their coding tasks.

    Be concise and direct. Use tools to gather information before answering.

    Note: In the NOOA framework, this entire class IS the agent.
    The docstring IS the system prompt. The methods ARE the tools.
    """

    def __init__(self, work_dir: Path | None = None):
        """Initialize the agent with a working directory."""
        self.work_dir = work_dir or Path.cwd()
        self.history: list[Message] = []
        self.provider = get_provider()
        self.tool_calls_made: int = 0
        self.total_tokens: int = 0

    # ── Tools: these methods are what the model can call ──────────

    def read_file(self, path: str) -> str:
        """Read the contents of a file.

        Args:
            path: Path to the file to read (relative to workspace).

        Returns:
            The file contents as a string.
        """
        try:
            file_path = (self.work_dir / path).resolve()
            if not file_path.exists():
                return f"Error: File not found: {path}"
            content = file_path.read_text(encoding="utf-8", errors="replace")
            if len(content) > 50_000:
                content = content[:50_000] + "\n... [truncated]"
            return content
        except Exception as e:
            return f"Error: {e}"

    def write_file(self, path: str, content: str) -> str:
        """Write content to a file, creating directories if needed.

        Args:
            path: Path to write (relative to workspace).
            content: Content to write.

        Returns:
            Confirmation message.
        """
        try:
            file_path = (self.work_dir / path).resolve()
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            return f"✅ Written {len(content)} chars to {path}"
        except Exception as e:
            return f"Error: {e}"

    def bash(self, command: str) -> str:
        """Run a shell command and return the output.

        Args:
            command: Shell command to execute.

        Returns:
            stdout + stderr output.
        """
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                timeout=30, cwd=self.work_dir,
            )
            output = (result.stdout + result.stderr).strip() or "(no output)"
            if len(output) > 10_000:
                output = output[:10_000] + "\n... [truncated]"
            return output
        except Exception as e:
            return f"Error: {e}"

    def list_files(self, path: str = ".") -> str:
        """List files and directories at the given path.

        Args:
            path: Directory to list (default: current directory).

        Returns:
            Formatted file listing.
        """
        try:
            dir_path = (self.work_dir / path).resolve()
            entries = sorted(dir_path.iterdir())
            lines = []
            for entry in entries:
                prefix = "📁" if entry.is_dir() else "📄"
                size = f" ({entry.stat().st_size}B)" if entry.is_file() else ""
                lines.append(f"{prefix} {entry.name}{size}")
            return "\n".join(lines) or "(empty)"
        except Exception as e:
            return f"Error: {e}"

    # ── Agent execution ──────────────────────────────────────────

    def _get_tool_schemas(self) -> list[dict]:
        """Generate tool schemas from our methods.

        In NOOA, this happens automatically — methods ARE tools.
        Here we manually generate schemas, but the key insight is
        that each schema maps 1:1 to a method on self.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": self.read_file.__doc__.split("\n")[0],
                    "parameters": {
                        "type": "object",
                        "properties": {"path": {"type": "string"}},
                        "required": ["path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": self.write_file.__doc__.split("\n")[0],
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "content": {"type": "string"},
                        },
                        "required": ["path", "content"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "bash",
                    "description": self.bash.__doc__.split("\n")[0],
                    "parameters": {
                        "type": "object",
                        "properties": {"command": {"type": "string"}},
                        "required": ["command"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_files",
                    "description": self.list_files.__doc__.split("\n")[0],
                    "parameters": {
                        "type": "object",
                        "properties": {"path": {"type": "string", "default": "."}},
                    },
                },
            },
        ]

    def _execute_tool(self, name: str, args: dict[str, Any]) -> str:
        """Execute a tool by calling the corresponding method on self.

        This is the key difference: tools are methods on the agent object.
        No global registry. No separate function table. Just `self.method()`.
        """
        method = getattr(self, name, None)
        if method is None:
            return f"Error: Unknown tool '{name}'"
        try:
            return method(**args)
        except TypeError as e:
            return f"Error calling {name}: {e}"

    async def run(self, user_message: str) -> str:
        """
        Run one complete agent turn.

        In NOOA, this would be a generation method with a `...` body:
            async def run(self, user_message: str) -> str:
                \"\"\"Process the user's request.\"\"\"
                ...
        The LLM would generate the implementation. Here we do it explicitly.
        """
        self.history.append(Message(role="user", content=user_message))
        system_prompt = self.__class__.__doc__ or "You are a helpful assistant."

        for iteration in range(10):
            messages = [Message(role="system", content=system_prompt)] + self.history
            response = await self.provider.chat(messages, tools=self._get_tool_schemas())

            self.total_tokens += (
                response.usage.get("prompt_tokens", 0) +
                response.usage.get("completion_tokens", 0)
            )

            if response.tool_calls:
                for tc in response.tool_calls:
                    self.tool_calls_made += 1
                    console.print(f"[dim]🔧 {tc.name}({json.dumps(tc.arguments)[:80]})[/dim]")
                    result = self._execute_tool(tc.name, tc.arguments)

                    self.history.append(Message(
                        role="assistant", content="",
                        tool_calls=[{"id": tc.id, "name": tc.name, "arguments": tc.arguments}],
                    ))
                    self.history.append(Message(role="tool", content=result, tool_call_id=tc.id))
                continue

            if response.content:
                self.history.append(Message(role="assistant", content=response.content))
                return response.content

        return "Max iterations reached."

    def stats(self) -> dict[str, int]:
        """Return agent statistics."""
        return {
            "tool_calls": self.tool_calls_made,
            "total_tokens": self.total_tokens,
            "history_length": len(self.history),
        }


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------
async def main() -> None:
    print_header(
        "Week 6 — Agent as Python Object",
        f"NOOA pattern | Model: {DEFAULT_MODEL}",
    )
    validate_setup()

    agent = CodingAgent()

    console.print("\n[bold]Notice:[/bold] The entire agent is one Python class.")
    console.print("[bold]Tools are methods. The docstring is the prompt. Fields are state.[/bold]\n")

    while True:
        try:
            user_input = console.input("\n[bold cyan]You:[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input or user_input.lower() in ("quit", "exit", "q"):
            break

        response = await agent.run(user_input)
        print_response(response)

        stats = agent.stats()
        console.print(f"[dim]📊 {stats['tool_calls']} tool calls | "
                      f"{stats['total_tokens']} total tokens[/dim]")


if __name__ == "__main__":
    asyncio.run(main())
