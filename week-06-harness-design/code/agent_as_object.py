"""Week 6 — an inspectable, testable agent-as-object harness.

The class owns its state and exposes actions as decorated methods.  Schemas are
derived from method signatures and docstrings, so adding a supported method
does not require updating a second registry.
"""

from __future__ import annotations

import argparse
import asyncio
import inspect
import json
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol, get_type_hints

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from shared.config import DEFAULT_MODEL, validate_setup
from shared.models import Message, ModelResponse, get_provider
from shared.utils import console, print_header, print_response


MAX_FILE_CHARS = 50_000
MAX_COMMAND_CHARS = 10_000
MAX_ITERATIONS = 10
SHELL_CONTROL_CHARACTERS = set("|&;<>()`$\n")
BLOCKED_COMMANDS = {"rm", "mv", "cp", "chmod", "chown", "dd", "mkfs", "mount", "sudo", "curl", "wget"}


class ChatProvider(Protocol):
    async def chat(self, messages: list[Message], tools: list[dict] | None = None) -> ModelResponse: ...


def tool(method: Callable[..., str]) -> Callable[..., str]:
    """Mark one public agent method as model-callable."""
    setattr(method, "_is_agent_tool", True)
    return method


def first_sentence(docstring: str | None) -> str:
    """Return a compact, model-facing tool description."""
    return next((line.strip() for line in (docstring or "").splitlines() if line.strip()), "No description provided.")


def json_type(annotation: type[Any]) -> str:
    """Map the small course tool surface to JSON Schema primitive types."""
    return {str: "string", int: "integer", float: "number", bool: "boolean"}.get(annotation, "string")


@dataclass(frozen=True)
class AgentStats:
    tool_calls: int
    total_tokens: int
    history_length: int


class CodingAgent:
    """A concise coding agent that gathers evidence before it answers."""

    def __init__(self, work_dir: Path | None = None, provider: ChatProvider | None = None):
        self.work_dir = (work_dir or Path.cwd()).resolve()
        if not self.work_dir.is_dir():
            raise ValueError(f"work_dir is not a directory: {self.work_dir}")
        self.history: list[Message] = []
        self.provider = provider or get_provider()
        self.tool_calls_made = 0
        self.total_tokens = 0

    def _resolve_path(self, path: str) -> Path:
        """Resolve a path and refuse escapes through ``..`` or symlinks."""
        candidate = (self.work_dir / path).resolve()
        if candidate != self.work_dir and self.work_dir not in candidate.parents:
            raise ValueError(f"Path escapes workspace: {path}")
        return candidate

    @tool
    def read_file(self, path: str) -> str:
        """Read one UTF-8 text file relative to the workspace."""
        try:
            file_path = self._resolve_path(path)
            if not file_path.is_file():
                return f"Error: File not found or not a regular file: {path}"
            content = file_path.read_text(encoding="utf-8", errors="replace")
            return content if len(content) <= MAX_FILE_CHARS else content[:MAX_FILE_CHARS] + "\n... [truncated]"
        except (OSError, ValueError) as exc:
            return f"Error reading file: {exc}"

    @tool
    def write_file(self, path: str, content: str) -> str:
        """Write one UTF-8 text file relative to the workspace."""
        try:
            file_path = self._resolve_path(path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            return f"Written {len(content)} characters to {file_path.relative_to(self.work_dir)}"
        except (OSError, ValueError) as exc:
            return f"Error writing file: {exc}"

    @tool
    def list_files(self, path: str = ".") -> str:
        """List direct entries in a workspace directory."""
        try:
            directory = self._resolve_path(path)
            if not directory.is_dir():
                return f"Error: Directory not found: {path}"
            return "\n".join(
                f"{'dir' if entry.is_dir() else 'file'}  {entry.name}"
                for entry in sorted(directory.iterdir(), key=lambda item: item.name.lower())
            ) or "(empty directory)"
        except (OSError, ValueError) as exc:
            return f"Error listing files: {exc}"

    @tool
    def bash(self, command: str) -> str:
        """Run one non-destructive command inside the workspace."""
        if any(character in command for character in SHELL_CONTROL_CHARACTERS):
            return "Error: Shell operators, substitutions, and multi-command input are not allowed."
        try:
            argv = shlex.split(command)
        except ValueError as exc:
            return f"Error parsing command: {exc}"
        if not argv:
            return "Error: Command cannot be empty."
        if argv[0] in BLOCKED_COMMANDS or (argv[0] == "git" and len(argv) > 1 and argv[1] in {"clean", "reset"}):
            return f"Error: Command '{argv[0]}' is blocked by the local safety policy."
        try:
            result = subprocess.run(argv, capture_output=True, text=True, timeout=30, cwd=self.work_dir, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return f"Error running command: {exc}"
        output = (result.stdout + ("\n" if result.stdout and result.stderr else "") + result.stderr).strip() or "(no output)"
        if result.returncode:
            output += f"\n[exit code: {result.returncode}]"
        return output if len(output) <= MAX_COMMAND_CHARS else output[:MAX_COMMAND_CHARS] + "\n... [truncated]"

    def _tool_methods(self) -> dict[str, Callable[..., str]]:
        """Discover decorated public methods in deterministic name order."""
        return {
            name: method for name, method in inspect.getmembers(self, predicate=inspect.ismethod)
            if getattr(method, "_is_agent_tool", False)
        }

    def tool_schemas(self) -> list[dict[str, Any]]:
        """Derive OpenAI-style schemas from method signatures and docstrings."""
        schemas: list[dict[str, Any]] = []
        for name, method in self._tool_methods().items():
            signature = inspect.signature(method)
            hints = get_type_hints(method)
            properties: dict[str, dict[str, Any]] = {}
            required: list[str] = []
            for parameter in signature.parameters.values():
                if parameter.name == "self":
                    continue
                definition: dict[str, Any] = {"type": json_type(hints.get(parameter.name, str))}
                if parameter.default is not inspect.Parameter.empty:
                    definition["default"] = parameter.default
                else:
                    required.append(parameter.name)
                properties[parameter.name] = definition
            schemas.append({"type": "function", "function": {
                "name": name,
                "description": first_sentence(method.__doc__),
                "parameters": {"type": "object", "properties": properties, "required": required},
            }})
        return schemas

    def execute_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """Run a discovered method and return controlled validation errors."""
        method = self._tool_methods().get(name)
        if method is None:
            return f"Error: Unknown tool '{name}'."
        try:
            inspect.signature(method).bind(**arguments)
        except TypeError as exc:
            return f"Error calling {name}: {exc}"
        try:
            return method(**arguments)
        except Exception as exc:  # Tool exceptions must become model observations.
            return f"Error executing {name}: {exc}"

    async def run(self, user_message: str) -> str:
        """Execute one bounded ReAct turn using this object as its tool surface."""
        self.history.append(Message(role="user", content=user_message))
        for _ in range(MAX_ITERATIONS):
            messages = [Message(role="system", content=self.__class__.__doc__ or "You are a coding agent.")] + self.history
            response = await self.provider.chat(messages, tools=self.tool_schemas())
            self.total_tokens += response.usage.get("prompt_tokens", 0) + response.usage.get("completion_tokens", 0)
            if response.tool_calls:
                for call in response.tool_calls:
                    self.tool_calls_made += 1
                    console.print(f"[dim]Tool: {call.name}({json.dumps(call.arguments)[:120]})[/dim]")
                    result = self.execute_tool(call.name, call.arguments)
                    self.history.extend([
                        Message(role="assistant", content="", tool_calls=[{"id": call.id, "name": call.name, "arguments": call.arguments}]),
                        Message(role="tool", content=result, tool_call_id=call.id),
                    ])
                continue
            if response.content:
                self.history.append(Message(role="assistant", content=response.content))
                return response.content
            return "Model returned neither a tool call nor a final response."
        return f"Agent reached its {MAX_ITERATIONS}-iteration safety limit."

    def stats(self) -> AgentStats:
        """Return immutable run statistics for reporting and tests."""
        return AgentStats(self.tool_calls_made, self.total_tokens, len(self.history))


async def main() -> None:
    parser = argparse.ArgumentParser(description="Week 6 agent-as-object demonstration")
    parser.add_argument("--work-dir", type=Path, default=Path.cwd(), help="Workspace exposed to the agent")
    args = parser.parse_args()
    print_header("Week 6 — Agent as Python Object", f"Model: {DEFAULT_MODEL}")
    validate_setup()
    agent = CodingAgent(work_dir=args.work_dir)
    console.print("[dim]Tools are decorated methods; schemas are derived at runtime. Use quit to exit.[/dim]")
    while True:
        try:
            user_input = console.input("\n[bold cyan]You:[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if user_input.lower() in {"quit", "exit", "q"}:
            break
        if user_input:
            print_response(await agent.run(user_input))
            console.print(f"[dim]{agent.stats()}[/dim]")


if __name__ == "__main__":
    asyncio.run(main())
