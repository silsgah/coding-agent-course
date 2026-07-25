# Week 7 — Parallel Subagents

> Fan out one call into N child agents. Each child gets its own budget and must return a structured report. Compare hand-rolled multi-agent vs NOOA-style single-agent.

---

## Learning Objectives

By the end of this week, you will:
1. Build a **subagent fan-out** that spawns N independent child agents
2. Give each child a **budget and report contract** (structured output)
3. Build a **coordinator** that merges child results
4. Compare **multi-agent swarm vs single-agent** on the same task

## The Big Idea

Some tasks decompose naturally: "explore 6 files" becomes 6 independent read-and-summarize calls. Running them sequentially wastes time. Running them in parallel — each in its own context — is both faster and uses the context window more efficiently.

But parallelism introduces coordination: Who decides the split? How do results merge? What if one child fails?

This week you'll build both approaches and compare:
1. **Subagent swarm** — N agents running in parallel, a coordinator merging results
2. **Single agent with skills** — NOOA-style, one agent methodically working through subtasks

The honest finding from NOOA's research: the single-agent approach often wins on simpler tasks, while the swarm wins on truly independent subtasks.

## Architecture

```
                        Coordinator
                    ┌───────────────────┐
   User task ──▶    │ Decompose task    │
                    │ into N subtasks   │
                    └───────┬───────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ Child 1  │ │ Child 2  │ │ Child 3  │
        │ Budget:  │ │ Budget:  │ │ Budget:  │
        │ 2k tokens│ │ 2k tokens│ │ 2k tokens│
        │          │ │          │ │          │
        │ Report:  │ │ Report:  │ │ Report:  │
        │ {struct} │ │ {struct} │ │ {struct} │
        └────┬─────┘ └────┬─────┘ └────┬─────┘
             │             │             │
              └─────────────┼─────────────┘
                            ▼
                    ┌───────────────────┐
                    │ Merge reports     │
                    │ Return answer     │
                    └───────────────────┘
```

## Code Walkthrough

### `subagent_swarm.py` — Fan-out N child agents

The coordinator:
1. Takes a task and decomposes it into independent subtasks
2. Spawns N child agents (one per subtask), each with its own context
3. Runs them in parallel using `asyncio.gather()`
4. Collects structured reports from each child
5. Merges reports into a final answer

### `budget_contract.py` — Per-child budget and structured reports

Each child agent:
- Gets a **token budget** (max tokens for its subtask)
- Must return a **structured report** (Pydantic model with specific fields)
- Fails gracefully if it exceeds budget or can't complete

### `single_vs_swarm.py` — Honest comparison

Run the same decomposable task both ways:
1. Multi-agent swarm (parallel children)
2. Single agent (sequential, NOOA-style method calls)

Compare: wall-clock time, total tokens, answer quality.

---

## Run It

```bash
cd week-07-parallel-subagents/code

# Fan-out demo
python subagent_swarm.py

# Budget and report contracts
python budget_contract.py

# Honest comparison
python single_vs_swarm.py
```

## Exercises

See [exercises/exercises.md](exercises/exercises.md)

## References

- [DecodingAI Lesson 6 — Subagents](../../building-a-coding-agent-from-scratch-course/lessons/06-subagents/) — agents catalog, parallel Explore fan-out
- [NOOA Self-extending agents](../../labs-OO-Agents/examples/README.md#self-extending-agents) — LLM-defined helper methods and fan-out
- [NOOA LLM cascading](../../labs-OO-Agents/examples/README.md#llm-cascading-resolution) — per-method model configuration

---

**Deliverable:** A working subagent swarm on a decomposable task, with an honest comparison against a simpler single-agent alternative.
