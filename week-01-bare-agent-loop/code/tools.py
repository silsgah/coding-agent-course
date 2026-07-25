"""
Week 1 — Tools
===============

The tools the agent can use. Each tool is a plain Python function
with a name, description, and parameter schema.

Design note: We deliberately keep tools as simple functions, not
classes or decorators. This makes it obvious that a "tool" is just
a function the model can call — nothing magical.

Inspired by the tool design in DecodingAI's coding agent course
(src/decode/tools/).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Tool implementations — plain Python functions
# ---------------------------------------------------------------------------
def read_file(path: str) -> str:
    """Read the contents of a file and return it as a string.

    Args:
        path: Path to the file to read.

    Returns:
        The file contents, or an error message if the file doesn't exist.
    """
    try:
        file_path = Path(path).resolve()
        if not file_path.exists():
            return f"Error: File not found: {path}"
        if not file_path.is_file():
            return f"Error: Not a file: {path}"
        content = file_path.read_text(encoding="utf-8", errors="replace")
        # Truncate very large files to avoid blowing up the context
        max_chars = 50_000
        if len(content) > max_chars:
            content = content[:max_chars] + f"\n\n... [truncated, {len(content)} total chars]"
        return content
    except Exception as e:
        return f"Error reading file: {e}"


def write_file(path: str, content: str) -> str:
    """Write content to a file, creating parent directories if needed.

    Args:
        path: Path to the file to write.
        content: The content to write to the file.

    Returns:
        A confirmation message or an error.
    """
    try:
        file_path = Path(path).resolve()
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return f"✅ Written {len(content)} chars to {file_path}"
    except Exception as e:
        return f"Error writing file: {e}"


def bash(command: str) -> str:
    """Run a shell command and return stdout + stderr.

    Args:
        command: The shell command to execute.

    Returns:
        Combined stdout and stderr output, or an error message.
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=Path.cwd(),
        )
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += ("\n" if output else "") + result.stderr
        if result.returncode != 0:
            output += f"\n[exit code: {result.returncode}]"
        if not output.strip():
            output = "(no output)"
        # Truncate long output
        max_chars = 10_000
        if len(output) > max_chars:
            output = output[:max_chars] + f"\n... [truncated, {len(output)} total chars]"
        return output
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 30 seconds"
    except Exception as e:
        return f"Error running command: {e}"


# ---------------------------------------------------------------------------
# Tool registry — name → function mapping
# ---------------------------------------------------------------------------
TOOLS: dict[str, Any] = {
    "read_file": read_file,
    "write_file": write_file,
    "bash": bash,
}


def execute_tool(name: str, arguments: dict[str, Any]) -> str:
    """Execute a tool by name with the given arguments."""
    if name not in TOOLS:
        return f"Error: Unknown tool '{name}'. Available: {list(TOOLS.keys())}"
    try:
        return TOOLS[name](**arguments)
    except TypeError as e:
        return f"Error calling tool '{name}': {e}"


# ---------------------------------------------------------------------------
# Tool schemas — what the model sees to know how to call tools
# ---------------------------------------------------------------------------
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file. Use this to examine code, configs, docs, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to read",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file. Creates parent directories if needed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to write",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file",
                    },
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "Run a shell command. Use for listing files, searching code, running tests, installing packages, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute",
                    }
                },
                "required": ["command"],
            },
        },
    },
]
