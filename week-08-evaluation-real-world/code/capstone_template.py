"""Scaffold a safe local capstone specification for Week 8."""

from __future__ import annotations

import argparse
from pathlib import Path


TEMPLATE = """# Coding Agent Capstone\n\n## Target repository\n- Repository:\n- Commit/ref:\n- Workspace or sandbox:\n\n## Agent task\nDescribe one bounded change the agent should attempt.\n\n## Authority\n- Filesystem scope:\n- Network policy:\n- Permission mode:\n- Maximum token/cost budget:\n- Maximum wall-clock time:\n\n## Benchmark tasks\n1.\n2.\n3.\n\n## Success criteria\n- Functional checks:\n- Regression checks:\n- Human review criteria:\n\n## Evidence to retain\n- Agent transcript or replay ID\n- Changed files/diff\n- Test output\n- Benchmark JSON\n- Review decision\n\n## Rollback plan\nExplain how the sandbox or branch is discarded if the run fails.\n"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a local Week 8 capstone specification")
    parser.add_argument("--output", type=Path, default=Path("CAPSTONE.md"))
    args = parser.parse_args()
    if args.output.exists():
        parser.error(f"Refusing to overwrite existing file: {args.output}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(TEMPLATE, encoding="utf-8")
    print(f"Capstone template written to {args.output}")


if __name__ == "__main__":
    main()
