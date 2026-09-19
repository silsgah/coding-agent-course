# Week 8 — Evaluation & Real-World Swarms

> Why a green test suite isn't enough: build isolated benchmarks and evidence packets for a human-reviewed delivery pipeline.

---

## Learning Objectives

By the end of this week, you will:
1. Build a **benchmark suite** that tests your agent on repeatable tasks
2. Create **regression probes** that catch when changes break capabilities
3. Identify what an online LLM-as-judge integration would need before it can be trusted
4. Build the local evidence packet for a human-reviewed issue → sandbox → PR workflow

## The Big Idea

You've built a working coding agent over 7 weeks. But how do you know it actually works? And how do you know it *keeps* working after you change something?

A green unit test suite is necessary but not sufficient. Unit tests verify individual components. What you need for an agent is:

1. **Benchmarks** — "Given this task, does the agent produce the right output?" Run 50 tasks, measure pass rate.
2. **Regression probes** — "Did my last change break something that used to work?" Run the same 10 tasks before and after.
3. **Online evals** — "For this live run, was the output good?" A calibrated LLM judge can score each response, but it needs separate implementation and validation.

This is the evaluation infrastructure that separates a demo from a product.

## Evaluation Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Evaluation Suite                          │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │  Benchmarks  │  │  Regression  │  │   Online Evals    │  │
│  │              │  │  Probes      │  │                   │  │
│  │  Local tasks │  │  Baselines   │  │  Future extension │  │
│  │  Pass/fail   │  │  Before/after│  │  Calibrated judge │  │
│  │  Repeatable  │  │  Regression  │  │  Separate review  │  │
│  └──────────────┘  └──────────────┘  └───────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │              End-to-End Pipeline                      │    │
│  │  Issue → Sandbox → Evidence Packet → Human Review → PR│    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

## The Issue → Review Pipeline

The capstone ties everything together:

1. A human supplies issue text to the local planner
2. The planner emits explicit exploration, implementation, verification, and review stages
3. Any implementation is run in a sandbox selected by the operator (Week 4)
4. The operator records changed files, tests, and benchmark evidence
5. A reviewer checks that evidence before authorizing a branch push or PR through a separate integration

## Code Walkthrough

### `benchmark_suite.py` — Repeatable task evaluation

Defines a set of benchmark tasks with expected outcomes:
- File creation tasks (did the file get created with the right content?)
- Code analysis tasks (did the agent identify the correct issues?)
- Multi-step tasks (did all steps complete successfully?)

### `github_issue_agent.py` — Issue → review packet

The full end-to-end flow:
1. Parses local issue text
2. Generates a staged plan with explicit authority boundaries
3. Records the required sandbox, test, benchmark, and approval evidence
4. Makes no external GitHub or repository write

### `capstone_template.py` — Capstone project scaffold

A template that students can customize for their capstone deliverable:
- Choose your own repo to work on
- Define your own benchmark tasks
- Write up your harness design choices

---

## Run It

```bash
cd week-08-evaluation-real-world/code

# Run the benchmark suite
python benchmark_suite.py

# Local issue → review-packet demo (no GitHub writes)
python github_issue_agent.py --issue "Add input validation to the CLI"

# Capstone template
python capstone_template.py
```

## Exercises / Capstone

See [exercises/exercises.md](exercises/exercises.md) — this week's exercises ARE the capstone.

## References

- [DecodingAI Lesson 7 — Evals](../../building-a-coding-agent-from-scratch-course/lessons/07-evals/) — benchmarks, regression, online evals
- [DecodingAI Lesson 8 — Ship](../../building-a-coding-agent-from-scratch-course/lessons/08-ship/) — cloud pipeline, env-scoped secrets
- [DecodingAI evals.md](../../building-a-coding-agent-from-scratch-course/running_the_code/evals.md) — eval commands

---

**Capstone Deliverable:** A scoped benchmark suite and a local review packet
for an issue-to-change workflow, with a short write-up of the harness design
and the evidence a human would require before an authorized PR is opened.
