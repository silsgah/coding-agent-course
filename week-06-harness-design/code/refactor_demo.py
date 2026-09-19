"""Offline structural comparison: Week 1 registry versus Week 6 object tools."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from agent_as_object import CodingAgent


def count_code_lines(path: Path) -> int:
    """Count non-empty, non-comment lines as a coarse teaching metric."""
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip() and not line.lstrip().startswith("#"))


def estimated_schema_tokens(schemas: list[dict]) -> int:
    """Use the same transparent four-characters-per-token estimate as Week 5."""
    return max(1, len(json.dumps(schemas, sort_keys=True)) // 4)


def comparison() -> dict[str, int]:
    """Return reproducible, source-level comparison data without a model call."""
    code_dir = Path(__file__).resolve().parent
    week_one_tools = code_dir.parent.parent / "week-01-bare-agent-loop" / "code" / "tools.py"
    namespace: dict = {}
    exec(compile(week_one_tools.read_text(encoding="utf-8"), str(week_one_tools), "exec"), namespace)
    agent = CodingAgent.__new__(CodingAgent)  # Schema discovery does not require a provider.
    return {
        "week1_tool_module_lines": count_code_lines(week_one_tools),
        "week6_agent_module_lines": count_code_lines(code_dir / "agent_as_object.py"),
        "week1_schema_tokens_estimate": estimated_schema_tokens(namespace["TOOL_SCHEMAS"]),
        "week6_schema_tokens_estimate": estimated_schema_tokens(agent.tool_schemas()),
        "week1_tool_count": len(namespace["TOOLS"]),
        "week6_tool_count": len(agent.tool_schemas()),
    }


def main() -> None:
    results = comparison()
    print("Week 6 — Refactor Comparison (offline structural metrics)\n")
    for label, value in results.items():
        print(f"{label.replace('_', ' ').capitalize()}: {value:,}")
    print("\nThese metrics describe code and schema size, not answer quality or live token usage.")


if __name__ == "__main__":
    main()
