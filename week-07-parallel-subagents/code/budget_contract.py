"""Contracts shared by the Week 7 coordinator and child agents."""

from __future__ import annotations

from dataclasses import dataclass, field


VALID_STATUSES = frozenset({"success", "partial", "failed"})


@dataclass(frozen=True)
class ChildBudget:
    """Hard limits owned by one child, not by the whole swarm."""

    max_tokens: int = 8_000
    max_iterations: int = 6
    timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        if self.max_tokens <= 0 or self.max_iterations <= 0 or self.timeout_seconds <= 0:
            raise ValueError("Child budget limits must be positive")


@dataclass(frozen=True)
class SubagentReport:
    """The only payload a child may return to its coordinator."""

    subtask: str
    status: str
    summary: str
    key_facts: tuple[str, ...] = field(default_factory=tuple)
    tokens_used: int = 0
    tool_calls: int = 0
    elapsed_seconds: float = 0.0
    error: str | None = None
    attempt: int = 1

    def __post_init__(self) -> None:
        if not self.subtask.strip():
            raise ValueError("A report requires a non-empty subtask")
        if self.status not in VALID_STATUSES:
            raise ValueError(f"Unknown report status: {self.status}")
        if self.tokens_used < 0 or self.tool_calls < 0 or self.elapsed_seconds < 0 or self.attempt < 1:
            raise ValueError("Report metrics must be non-negative and attempt positive")
        if len(self.summary) > 2_000:
            raise ValueError("Report summaries are capped at 2,000 characters")
        if len(self.key_facts) > 10:
            raise ValueError("Reports may contain at most ten key facts")

    @classmethod
    def failed(cls, subtask: str, error: str, elapsed_seconds: float, attempt: int = 1) -> "SubagentReport":
        return cls(subtask, "failed", "", (), 0, 0, elapsed_seconds, error[:500], attempt)


def main() -> None:
    """Print the contract shape without requiring a provider or API key."""
    budget = ChildBudget()
    report = SubagentReport("Inspect README", "success", "README is present.", ("README.md exists",), 120, 1, 0.2)
    print("Week 7 — Child Budget and Report Contract")
    print(f"Budget: {budget}\nReport: {report}")


if __name__ == "__main__":
    main()
