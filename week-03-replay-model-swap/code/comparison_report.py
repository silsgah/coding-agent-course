"""Create a Markdown comparison report from Week 3 replay sessions.

Usage:
    python comparison_report.py --runs sessions/original sessions/replay-gpt
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from replay_core import load_events, load_metrics


PRICES_PER_MILLION = {
    "gemini-flash": (0.075, 0.30),
    "gpt-4o-mini": (0.15, 0.60),
    "claude-haiku": (0.25, 1.25),
}


def price_for_model(model: str) -> tuple[float, float] | None:
    normalized = model.lower()
    for name, price in PRICES_PER_MILLION.items():
        if name in normalized:
            return price
    return None


def estimated_cost_usd(metrics: dict) -> float | None:
    price = price_for_model(metrics.get("model", ""))
    if not price:
        return None
    return metrics.get("prompt_tokens", 0) * price[0] / 1_000_000 + metrics.get("completion_tokens", 0) * price[1] / 1_000_000


def run_summary(session_dir: Path) -> dict:
    metrics = load_metrics(session_dir)
    events = load_events(session_dir)
    tool_calls = sum(event["event_type"] == "tool_call" for event in events)
    answer = next((event["data"]["response"] for event in reversed(events) if event["event_type"] == "assistant_response"), "")
    return {
        "name": session_dir.name,
        "model": metrics.get("model", "unknown"),
        "prompt_tokens": metrics.get("prompt_tokens", 0),
        "completion_tokens": metrics.get("completion_tokens", 0),
        "total_tokens": metrics.get("total_tokens", metrics.get("prompt_tokens", 0) + metrics.get("completion_tokens", 0)),
        "tool_calls": metrics.get("tool_calls", tool_calls),
        "elapsed_seconds": metrics.get("elapsed_seconds", 0),
        "answer": metrics.get("answer", answer),
        "error": metrics.get("error"),
        "cost": estimated_cost_usd(metrics),
    }


def markdown_report(summaries: list[dict]) -> str:
    lines = ["# Replay Comparison Report", "", "| Run | Model | Tool calls | Tokens | Time | Est. cost |", "| --- | --- | ---: | ---: | ---: | ---: |"]
    for item in summaries:
        cost = "n/a" if item["cost"] is None else f"${item['cost']:.6f}"
        lines.append(f"| {item['name']} | {item['model']} | {item['tool_calls']} | {item['total_tokens']} | {item['elapsed_seconds']:.2f}s | {cost} |")
    lines.append("\n## Answers")
    for item in summaries:
        lines.extend([f"\n### {item['name']} — {item['model']}", "", item["answer"] or "_No final answer recorded._"])
        if item["error"]:
            lines.extend(["", f"**Error:** {item['error']}"])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a Week 3 replay comparison report")
    parser.add_argument("--runs", nargs="+", required=True, help="Session directories to compare")
    parser.add_argument("--output", default="comparison_report.md", help="Markdown output path")
    args = parser.parse_args()
    report = markdown_report([run_summary(Path(run)) for run in args.runs])
    output = Path(args.output)
    output.write_text(report, encoding="utf-8")
    print(f"Report written to {output}")


if __name__ == "__main__":
    main()
