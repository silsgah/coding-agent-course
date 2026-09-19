"""Create a local, reviewable issue-to-agent work packet.

This deliberately stops before external GitHub writes. A human reviews the
packet, selects a sandboxed execution environment, and creates a PR through an
authorized CI or GitHub integration.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def plan_issue(issue: str) -> dict:
    """Create a transparent conservative plan without a model or network call."""
    normalized = " ".join(issue.split())
    if not normalized:
        raise ValueError("Issue text cannot be empty")
    return {
        "version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "issue": normalized,
        "status": "requires_human_approval",
        "proposed_stages": [
            {"name": "explore", "authority": "read-only sandbox", "goal": "Locate relevant files and tests."},
            {"name": "implement", "authority": "write-enabled sandbox", "goal": "Make the smallest validated change."},
            {"name": "verify", "authority": "sandboxed test runner", "goal": "Run targeted checks and record results."},
            {"name": "review", "authority": "human", "goal": "Review diff, evidence, and release decision."},
        ],
        "required_evidence": ["sandbox identifier", "changed-file list", "test output", "benchmark results", "human approval"],
        "external_effects": "None. This command does not call GitHub, create branches, or open pull requests.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a safe local issue-to-agent review packet")
    parser.add_argument("--issue", required=True, help="Issue text to plan")
    parser.add_argument("--output", type=Path, default=Path("issue_review_packet.json"))
    args = parser.parse_args()
    packet = plan_issue(args.issue)
    args.output.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    print(f"Review packet written to {args.output}")
    print("No GitHub or repository changes were made.")


if __name__ == "__main__":
    main()
