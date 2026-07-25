"""
Week 5 — Memory Strategies
============================

Three memory mechanisms that feed the agent curated context:

1. AGENTS.md — project-specific instructions (loaded at session start)
2. MEMORY.md — things the agent learned during previous sessions
3. Skills — curated domain knowledge loaded on demand

Inspired by:
- DecodingAI's memory system (src/decode/memory/)
- NOOA's Skills and Context Blocks (examples/quickstart/10_skills.py)
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from shared.config import validate_setup
from shared.utils import print_header, console

from rich.panel import Panel
from rich.syntax import Syntax


# ---------------------------------------------------------------------------
# Memory: AGENTS.md — project-specific instructions
# ---------------------------------------------------------------------------
class AgentsMemory:
    """
    Loads AGENTS.md from the project root.

    This file tells the agent how to work with this specific project:
    - Coding conventions
    - Test commands
    - Architecture notes
    - Things to avoid
    """

    def __init__(self, project_dir: Path):
        self.path = project_dir / "AGENTS.md"

    def load(self) -> str:
        """Load AGENTS.md content, or return empty if not found."""
        if self.path.exists():
            content = self.path.read_text(encoding="utf-8")
            console.print(f"[green]📋 Loaded AGENTS.md ({len(content)} chars)[/green]")
            return content
        console.print("[dim]No AGENTS.md found — create one to give the agent project-specific instructions.[/dim]")
        return ""

    @staticmethod
    def template() -> str:
        """Return a template AGENTS.md for new projects."""
        return """\
# AGENTS.md — Instructions for AI Agents

## Project Overview
This project is [describe your project].

## Coding Conventions
- Use [language/framework conventions]
- Tests go in `tests/`
- Run tests with: `pytest`

## Architecture
- [Describe key modules and their responsibilities]

## Things to Avoid
- Don't modify files in `vendor/` or `generated/`
- Don't commit `.env` or secrets

## Common Tasks
- To add a feature: [describe the process]
- To fix a bug: [describe the process]
"""


# ---------------------------------------------------------------------------
# Memory: MEMORY.md — learned knowledge
# ---------------------------------------------------------------------------
class LearnedMemory:
    """
    Loads and saves MEMORY.md — things the agent learned.

    After each session, the agent can write back observations:
    - File paths it discovered
    - Patterns it noticed
    - Mistakes it made and corrections
    """

    def __init__(self, project_dir: Path):
        self.path = project_dir / ".agent" / "MEMORY.md"

    def load(self) -> str:
        """Load MEMORY.md content."""
        if self.path.exists():
            content = self.path.read_text(encoding="utf-8")
            console.print(f"[green]🧠 Loaded MEMORY.md ({len(content)} chars)[/green]")
            return content
        return ""

    def save(self, content: str) -> None:
        """Save updated memory."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(content, encoding="utf-8")
        console.print(f"[green]💾 Saved MEMORY.md ({len(content)} chars)[/green]")

    def append(self, entry: str) -> None:
        """Append a new memory entry."""
        existing = self.load()
        timestamp = __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M")
        updated = existing + f"\n\n## {timestamp}\n{entry}"
        self.save(updated)


# ---------------------------------------------------------------------------
# Skills — curated domain knowledge
# ---------------------------------------------------------------------------
class Skill:
    """
    A skill is a curated piece of domain knowledge the agent
    can load on demand.

    Skills are stored as markdown files in a `skills/` directory.
    Each skill has:
    - A name (from the filename)
    - A description (first line of the file)
    - Content (the full file)

    Inspired by NOOA's TextSkill (examples/quickstart/10_skills.py)
    and DecodingAI's skills dispatch (src/decode/tools/).
    """

    def __init__(self, path: Path):
        self.path = path
        self.name = path.stem
        content = path.read_text(encoding="utf-8")
        lines = content.strip().split("\n")
        self.description = lines[0].lstrip("# ").strip() if lines else self.name
        self.content = content

    def __repr__(self) -> str:
        return f"Skill({self.name!r}: {self.description[:60]})"


class SkillsManager:
    """Discover and load skills from a directory."""

    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir
        self.skills: dict[str, Skill] = {}
        self._discover()

    def _discover(self) -> None:
        """Find all .md files in the skills directory."""
        if not self.skills_dir.exists():
            return
        for path in sorted(self.skills_dir.glob("*.md")):
            skill = Skill(path)
            self.skills[skill.name] = skill

        if self.skills:
            console.print(f"[green]🎯 Found {len(self.skills)} skills: "
                          f"{', '.join(self.skills.keys())}[/green]")

    def get(self, name: str) -> Skill | None:
        """Get a skill by name."""
        return self.skills.get(name)

    def list_skills(self) -> list[str]:
        """List all available skill names."""
        return list(self.skills.keys())

    def inject(self, name: str) -> str:
        """Get skill content ready for injection into the system prompt."""
        skill = self.get(name)
        if skill:
            return f"\n\n---\n[Skill: {skill.name}]\n{skill.content}\n---\n"
        return ""


# ---------------------------------------------------------------------------
# Demo: show all three memory strategies
# ---------------------------------------------------------------------------
def create_demo_skills(skills_dir: Path) -> None:
    """Create example skills for the demo."""
    skills_dir.mkdir(parents=True, exist_ok=True)

    (skills_dir / "python-best-practices.md").write_text("""\
# Python Best Practices

## Formatting
- Use `ruff` for linting and formatting
- Line length: 100 characters
- Use type hints for all function signatures

## Testing
- Use `pytest` for all tests
- Aim for >80% coverage
- Put tests in `tests/` mirroring `src/` structure

## Common Patterns
- Use `dataclasses` or `pydantic` for data models
- Prefer `pathlib.Path` over `os.path`
- Use `asyncio` for I/O-bound operations
""")

    (skills_dir / "git-workflow.md").write_text("""\
# Git Workflow

## Branch Naming
- feature/description
- fix/description
- refactor/description

## Commit Messages
- Use conventional commits: feat:, fix:, docs:, refactor:, test:
- Keep the first line under 72 characters
- Reference issue numbers when applicable

## PR Process
- One PR per feature/fix
- Include tests
- Update documentation
""")


async def main() -> None:
    print_header("Week 5 — Memory Strategies", "AGENTS.md, MEMORY.md, and Skills")
    validate_setup()

    project_dir = Path.cwd()

    # 1. AGENTS.md
    console.print("\n[bold]═══ 1. AGENTS.md — Project Instructions ═══[/bold]")
    agents = AgentsMemory(project_dir)
    agents_content = agents.load()
    if not agents_content:
        console.print("\n[dim]Template for a new project:[/dim]")
        console.print(Panel(AgentsMemory.template(), title="AGENTS.md Template"))

    # 2. MEMORY.md
    console.print("\n[bold]═══ 2. MEMORY.md — Learned Knowledge ═══[/bold]")
    memory = LearnedMemory(project_dir)
    memory_content = memory.load()
    if not memory_content:
        console.print("[dim]No memories yet. The agent writes these during sessions.[/dim]")
        memory.append("Discovered that this project uses Python 3.12 with pytest for testing.")
        memory.append("The main source code is in src/ and tests mirror the structure.")
        console.print("[green]✅ Added example memories[/green]")

    # 3. Skills
    console.print("\n[bold]═══ 3. Skills — Domain Knowledge ═══[/bold]")
    skills_dir = project_dir / ".agent" / "skills"
    create_demo_skills(skills_dir)
    skills = SkillsManager(skills_dir)

    for name in skills.list_skills():
        skill = skills.get(name)
        if skill:
            console.print(f"\n[cyan]Skill: {skill.name}[/cyan]")
            console.print(f"[dim]{skill.description}[/dim]")
            console.print(f"[dim]{len(skill.content)} chars of curated knowledge[/dim]")

    # Show how it all fits into the system prompt
    console.print("\n[bold]═══ Combined System Prompt ═══[/bold]")
    system_prompt_parts = [
        "You are a helpful coding assistant.",
    ]
    if agents_content:
        system_prompt_parts.append(f"\n[Project Instructions]\n{agents_content[:500]}")
    memory_content = memory.load()
    if memory_content:
        system_prompt_parts.append(f"\n[Agent Memory]\n{memory_content[:500]}")

    combined = "\n".join(system_prompt_parts)
    console.print(f"[dim]Total system prompt: ~{len(combined) // 4} tokens[/dim]")


if __name__ == "__main__":
    asyncio.run(main())
