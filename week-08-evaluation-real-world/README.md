# Week 8 — Evaluation & Real-World Swarms

> Why a green test suite isn't enough: build benchmarks, regression probes, and online evals. End-to-end: a teammate labels a GitHub issue, the swarm returns a reviewed pull request.

---

## Learning Objectives

By the end of this week, you will:
1. Build a **benchmark suite** that tests your agent on repeatable tasks
2. Create **regression probes** that catch when changes break capabilities
3. Implement **online evals** — LLM-as-judge scoring of live runs
4. Build the **full pipeline**: GitHub issue → agent swarm → reviewed PR

## The Big Idea

You've built a working coding agent over 7 weeks. But how do you know it actually works? And how do you know it *keeps* working after you change something?

A green unit test suite is necessary but not sufficient. Unit tests verify individual components. What you need for an agent is:

1. **Benchmarks** — "Given this task, does the agent produce the right output?" Run 50 tasks, measure pass rate.
2. **Regression probes** — "Did my last change break something that used to work?" Run the same 10 tasks before and after.
3. **Online evals** — "For this live run, was the output good?" Use an LLM judge to score each response.

This is the evaluation infrastructure that separates a demo from a product.

## Evaluation Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Evaluation Suite                          │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │  Benchmarks  │  │  Regression  │  │   Online Evals    │  │
│  │              │  │  Probes      │  │                   │  │
│  │  50 tasks    │  │  10 tasks    │  │  LLM-as-judge     │  │
│  │  Pass/fail   │  │  Before/after│  │  Score 1-5        │  │
│  │  Monthly     │  │  Every PR    │  │  Every run        │  │
│  └──────────────┘  └──────────────┘  └───────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │              End-to-End Pipeline                      │    │
│  │  GitHub Issue → Agent Swarm → Code → Tests → PR      │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

## The GitHub Issue → PR Pipeline

The capstone ties everything together:

1. A teammate **labels a GitHub issue** with `agent-ready`
2. The system **decomposes** the issue into subtasks (Week 7)
3. A **swarm of agents** works the subtasks in parallel
4. Each agent works in its own **sandbox** (Week 4)
5. Results are **merged** and a **PR** is created
6. An **LLM reviewer** checks the PR for quality
7. The PR is **submitted** for human review

## Code Walkthrough

### `benchmark_suite.py` — Repeatable task evaluation

Defines a set of benchmark tasks with expected outcomes:
- File creation tasks (did the file get created with the right content?)
- Code analysis tasks (did the agent identify the correct issues?)
- Multi-step tasks (did all steps complete successfully?)

### `github_issue_agent.py` — Issue → PR pipeline

The full end-to-end flow:
1. Parse a GitHub issue (or a local issue file)
2. Decompose into subtasks
3. Run the swarm (Week 7)
4. Collect changes
5. Generate a PR description
6. Run the eval suite on the result

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

# End-to-end issue → PR demo
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

**Capstone Deliverable:** An agent (or agent swarm) that closes a real GitHub issue, benchmarked on accuracy, reliability, and token cost — with a short write-up justifying your harness design choices.
