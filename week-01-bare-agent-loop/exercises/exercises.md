# Week 1 — Exercises

## Exercise 1: Add a `list_dir` tool

The agent currently has `read_file`, `write_file`, and `bash`. Add a `list_dir` tool that:
- Takes a `path` argument (default: current directory)
- Returns a formatted listing of files and directories
- Classifies its risk as "low"

**Hint:** Look at how `read_file` is registered — same pattern.

**Bonus:** Make it show file sizes and modification dates.

---

## Exercise 2: Deny a tool call and watch the model adapt

1. Ask the agent to create a file
2. When the permission gate asks, deny it (`n`)
3. Watch what the model does next — does it give up? Try again differently?

**Think about:** What should the agent do when denied? This is a harness design question, not a model question.

---

## Exercise 3: Add tool call counting

Modify `agent.py` to track:
- How many tool calls per turn
- Total tool calls across the session
- Which tools are called most often

Print a summary after each turn. This is your first step toward observability (Week 8).

---

## Exercise 4: Multi-turn conversation

The current loop handles one turn. Extend it to:
1. Keep the conversation history between turns
2. Let the agent reference earlier turns ("the file I showed you before...")
3. What happens to the history after 20 turns? (Preview of Week 5: context budget)

**Already done?** The REPL in `agent.py` already maintains `history` — this exercise is about understanding *why* that matters.

---

## Exercise 5: Break the agent intentionally

Try these and observe the behavior:
1. Ask the agent to read a file that doesn't exist
2. Ask it to run `sleep 60` (what happens with the 30s timeout?)
3. Ask it to read a very large file (what happens at the 50k char truncation?)
4. Give it a prompt with no clear task ("tell me about yourself")

**Key insight:** Every one of these edge cases is a harness problem, not a model problem.

---

## Solutions

### Exercise 1 — `list_dir` tool

```python
# Add to tools.py

import os

def list_dir(path: str = ".") -> str:
    """List files and directories at the given path.

    Args:
        path: Directory path to list. Defaults to current directory.
    """
    try:
        dir_path = Path(path).resolve()
        if not dir_path.exists():
            return f"Error: Directory not found: {path}"
        if not dir_path.is_dir():
            return f"Error: Not a directory: {path}"

        entries = sorted(dir_path.iterdir())
        lines = []
        for entry in entries:
            prefix = "📁" if entry.is_dir() else "📄"
            size = f" ({entry.stat().st_size} bytes)" if entry.is_file() else ""
            lines.append(f"{prefix} {entry.name}{size}")

        return "\n".join(lines) if lines else "(empty directory)"
    except Exception as e:
        return f"Error listing directory: {e}"

# Register it:
TOOLS["list_dir"] = list_dir
RISK_LEVELS["list_dir"] = "low"  # in permission_gate.py

# Add schema to TOOL_SCHEMAS:
{
    "type": "function",
    "function": {
        "name": "list_dir",
        "description": "List files and directories at a path.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path (default: current dir)",
                    "default": ".",
                }
            },
        },
    },
}
```

### Exercise 3 — Tool call counting

```python
# Add to agent.py, inside agent_loop:

tool_stats = {"total": 0, "by_tool": {}}

# After each tool call execution:
tool_stats["total"] += 1
tool_stats["by_tool"][tool_call.name] = tool_stats["by_tool"].get(tool_call.name, 0) + 1

# After the loop:
console.print(f"[dim]📊 Tool calls this turn: {tool_stats['total']}[/dim]")
for name, count in tool_stats["by_tool"].items():
    console.print(f"[dim]   {name}: {count}[/dim]")
```
