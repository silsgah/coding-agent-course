"""
Week 4 — Docker Workspace Isolation
=====================================

Run tool execution inside a Docker container while keeping
the agent loop on the host machine.

The container:
  - Mounts only the project directory
  - Has no network access by default
  - Has no access to host secrets
  - Is destroyed after the session

Requirements:
  - Docker daemon running
  - pip install docker

Usage:
    python docker_workspace.py

Inspired by the sandbox system in DecodingAI's coding agent
(src/decode/sandbox/).
"""

from __future__ import annotations

import asyncio
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from shared.config import validate_setup, DEFAULT_MODEL
from shared.models import get_provider, Message
from shared.utils import print_header, print_tool_call, print_response, print_usage, console


# ---------------------------------------------------------------------------
# Docker sandbox
# ---------------------------------------------------------------------------
class DockerSandbox:
    """Execute tool calls inside a Docker container."""

    IMAGE = "python:3.12-slim"

    def __init__(self, work_dir: Path | None = None):
        self.work_dir = work_dir or Path.cwd()
        self.container = None
        self._docker_available = False

        try:
            import docker
            self.client = docker.from_env()
            self.client.ping()
            self._docker_available = True
            console.print("[green]🐳 Docker is available[/green]")
        except Exception as e:
            console.print(f"[yellow]⚠️ Docker not available: {e}[/yellow]")
            console.print("[yellow]   Falling back to local execution[/yellow]")

    @property
    def is_available(self) -> bool:
        return self._docker_available

    def execute_bash(self, command: str) -> str:
        """Execute a bash command inside the Docker container."""
        if not self._docker_available:
            return self._local_bash(command)

        import docker

        try:
            result = self.client.containers.run(
                self.IMAGE,
                command=f"bash -c '{command}'",
                volumes={
                    str(self.work_dir.resolve()): {
                        "bind": "/workspace",
                        "mode": "rw",
                    }
                },
                working_dir="/workspace",
                network_mode="none",      # No network access
                mem_limit="512m",          # Memory limit
                remove=True,              # Auto-cleanup
                timeout=30,
            )
            return result.decode("utf-8", errors="replace")
        except docker.errors.ContainerError as e:
            return f"Container error (exit {e.exit_status}): {e.stderr.decode()}"
        except Exception as e:
            return f"Docker error: {e}"

    def execute_read_file(self, path: str) -> str:
        """Read a file from the workspace."""
        # File reads can be done locally — they're safe
        try:
            file_path = (self.work_dir / path).resolve()
            if not str(file_path).startswith(str(self.work_dir.resolve())):
                return "Error: Path escapes workspace"
            return file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return f"Error: {e}"

    def execute_write_file(self, path: str, content: str) -> str:
        """Write a file to the workspace."""
        try:
            file_path = (self.work_dir / path).resolve()
            if not str(file_path).startswith(str(self.work_dir.resolve())):
                return "Error: Path escapes workspace"
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            return f"✅ Written to {path}"
        except Exception as e:
            return f"Error: {e}"

    def execute_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """Execute any tool through the sandbox."""
        if name == "bash":
            return self.execute_bash(arguments.get("command", ""))
        elif name == "read_file":
            return self.execute_read_file(arguments.get("path", ""))
        elif name == "write_file":
            return self.execute_write_file(
                arguments.get("path", ""),
                arguments.get("content", ""),
            )
        else:
            return f"Unknown tool: {name}"

    def _local_bash(self, command: str) -> str:
        """Fallback: local bash execution (when Docker unavailable)."""
        import subprocess
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                timeout=30, cwd=self.work_dir,
            )
            output = result.stdout + result.stderr
            return output.strip() or "(no output)"
        except Exception as e:
            return f"Error: {e}"


# ---------------------------------------------------------------------------
# Agent loop with Docker sandbox
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """\
You are a helpful coding assistant working inside an isolated workspace.
You can read files, write files, and run shell commands safely —
everything executes in a sandbox.
"""

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file from the workspace.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Path relative to workspace"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file in the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path relative to workspace"},
                    "content": {"type": "string", "description": "Content to write"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "Run a shell command in the sandboxed workspace.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string", "description": "Shell command to execute"}},
                "required": ["command"],
            },
        },
    },
]


async def main() -> None:
    print_header(
        "Week 4 — Docker Workspace",
        f"Model: {DEFAULT_MODEL} | Sandboxed execution",
    )
    validate_setup()

    # Create a temporary workspace
    workspace = Path(tempfile.mkdtemp(prefix="agent-workspace-"))
    console.print(f"[dim]Workspace: {workspace}[/dim]")

    sandbox = DockerSandbox(work_dir=workspace)
    provider = get_provider()
    history: list[Message] = []

    while True:
        try:
            user_input = console.input("\n[bold cyan]You:[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input or user_input.lower() in ("quit", "exit", "q"):
            break

        history.append(Message(role="user", content=user_input))

        for iteration in range(10):
            messages = [Message(role="system", content=SYSTEM_PROMPT)] + history
            response = await provider.chat(messages, tools=TOOL_SCHEMAS)
            print_usage(response.usage)

            if response.tool_calls:
                for tc in response.tool_calls:
                    print_tool_call(tc.name, tc.arguments)

                    # Execute through sandbox — no permission gate needed!
                    result = sandbox.execute_tool(tc.name, tc.arguments)
                    console.print(f"[dim]🐳 Sandboxed result ({len(result)} chars)[/dim]")

                    history.append(Message(
                        role="assistant", content="",
                        tool_calls=[{"id": tc.id, "name": tc.name, "arguments": tc.arguments}],
                    ))
                    history.append(Message(role="tool", content=result, tool_call_id=tc.id))
                continue

            if response.content:
                history.append(Message(role="assistant", content=response.content))
                print_response(response.content)
                break

    # Cleanup
    import shutil
    shutil.rmtree(workspace, ignore_errors=True)
    console.print("[dim]Workspace cleaned up.[/dim]")


if __name__ == "__main__":
    asyncio.run(main())
