"""Compare growing conversation context with method-boundary context.

This is an offline, transparent model of the NOOA design idea: hand a focused
subtask to a fresh method rather than carry every prior tool result forward.
It estimates context *sent to the model*, not answer quality.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from shared.models import Message

from context_budget import ContextBudget, estimate_message_tokens, estimate_tokens


SYSTEM_PROMPT = "You are a coding agent. Work carefully and report concise results."
DEFAULT_STEPS = [
    "Inspect the project structure.",
    "Read the configuration and identify the test command.",
    "Implement the requested change.",
    "Run the relevant tests and explain the outcome.",
]


@dataclass
class StrategyResult:
    name: str
    input_tokens: int
    peak_context_tokens: int
    compactions: int


def compare_strategies(steps: list[str], tool_result_chars: int, max_tokens: int, threshold: float) -> list[StrategyResult]:
    """Estimate the prompt burden of two ways of sequencing the same work."""
    system_tokens = estimate_tokens(SYSTEM_PROMPT)
    history = [Message(role="system", content=SYSTEM_PROMPT)]
    growing_input = 0
    peak = system_tokens
    compactions = 0
    budget = ContextBudget(max_tokens=max_tokens, compaction_threshold=threshold)
    budget.system_tokens = system_tokens

    for number, step in enumerate(steps, start=1):
        growing_input += sum(estimate_message_tokens(message) for message in history)
        history.extend([
            Message(role="user", content=step),
            Message(role="assistant", content="I will inspect the relevant files."),
            Message(role="tool", content=f"Step {number} result: " + "x" * tool_result_chars, tool_call_id="demo"),
        ])
        budget.update_history(history[1:])
        peak = max(peak, budget.used_tokens)
        if budget.needs_compaction:
            # Offline stand-in for a real summary: retain the system prompt,
            # a concise state handoff, and the latest action/result pair.
            compactions += 1
            history = [history[0], Message(role="assistant", content="Summary of earlier completed work."), *history[-2:]]
            budget.update_history(history[1:])

    method_input = sum(system_tokens + estimate_tokens(step) for step in steps)
    method_peak = max((system_tokens + estimate_tokens(step) for step in steps), default=system_tokens)
    return [
        StrategyResult("Growing history + compaction", growing_input, peak, compactions),
        StrategyResult("Method boundary (fresh context)", method_input, method_peak, 0),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline Week 5 context-strategy comparison")
    parser.add_argument("--steps", type=int, default=len(DEFAULT_STEPS), help="Number of representative subtasks")
    parser.add_argument("--tool-result-chars", type=int, default=4_000, help="Characters returned by each representative tool call")
    parser.add_argument("--max-tokens", type=int, default=4_000, help="Illustrative context-window size")
    parser.add_argument("--threshold", type=float, default=0.8, help="Compaction threshold between 0 and 1")
    args = parser.parse_args()
    if args.steps < 1 or args.tool_result_chars < 0 or not 0 < args.threshold <= 1:
        parser.error("steps must be positive, tool-result-chars non-negative, and threshold in (0, 1]")

    steps = [DEFAULT_STEPS[index % len(DEFAULT_STEPS)] for index in range(args.steps)]
    results = compare_strategies(steps, args.tool_result_chars, args.max_tokens, args.threshold)
    print("Week 5 — Context Strategy Comparison (offline estimate)\n")
    print("Strategy                         Input tokens   Peak context   Compactions")
    for result in results:
        print(f"{result.name:<32} {result.input_tokens:>12,} {result.peak_context_tokens:>14,} {result.compactions:>13}")
    print("\nThis estimates prompt volume only. It does not measure answer quality or live provider usage.")


if __name__ == "__main__":
    main()
