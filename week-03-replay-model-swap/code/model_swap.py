"""Create one replay branch per model from exactly the same checkpoint.

Usage:
    python model_swap.py --original sessions/run-20260830-120000 \
      --models gemini-2.0-flash gpt-4o-mini --from-step 1
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from shared.config import validate_setup
from shared.utils import console, print_header

from replay_harness import replay_from, session_name
from replay_core import RunMetrics


def safe_model_name(model: str) -> str:
    """Make a readable directory suffix without treating model text as a path."""
    return "".join(character if character.isalnum() else "-" for character in model).strip("-")


async def run_model_swap(original: Path, models: list[str], from_step: int, sessions_dir: Path) -> list[tuple[Path, RunMetrics]]:
    """Replay an identical checkpoint prefix once for each requested model."""
    results: list[tuple[Path, RunMetrics]] = []
    for model in models:
        target = sessions_dir / f"{session_name('swap')}-{safe_model_name(model)}"
        console.print(f"[cyan]Replaying with {model}...[/cyan]")
        results.append((target, await replay_from(original, from_step, target, model)))
    return results


async def main() -> None:
    parser = argparse.ArgumentParser(description="Compare models by replaying one checkpoint")
    parser.add_argument("--original", required=True, help="Checkpoint session to fork")
    parser.add_argument("--models", nargs="+", required=True, help="Models to compare")
    parser.add_argument("--from-step", type=int, default=0, help="Completed tool step at which to fork")
    parser.add_argument("--sessions-dir", default="sessions", help="Directory for new replay branches")
    args = parser.parse_args()

    print_header("Week 3 — Model Swap", "Same checkpoint prefix, same tools, different model")
    validate_setup()
    results = await run_model_swap(Path(args.original), args.models, args.from_step, Path(args.sessions_dir))
    console.print("\n[bold]Results[/bold]")
    for directory, metrics in results:
        status = metrics.error or "complete"
        console.print(f"• {metrics.model}: {metrics.tool_calls} tool call(s), {metrics.total_tokens} tokens, {status} — {directory}")
    console.print("\nRun comparison_report.py with the listed directories to produce a Markdown report.")


if __name__ == "__main__":
    asyncio.run(main())
