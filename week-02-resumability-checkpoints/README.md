# Week 2 — Resumability & Checkpoints

> Simulate `kill -9` mid-task. Build checkpointing so a resumed run never re-pays for already-finished work.

---

## Learning Objectives

By the end of this week, you will:
1. Understand why **durability** matters for any real agent deployment
2. Build a **checkpoint system** that persists agent state to disk
3. **Resume** a crashed run without replaying already-completed tool calls
4. Know the difference between **replayable history** and **durable state**

## The Big Idea

Your Week 1 agent has a fatal flaw: if the process dies — power cut, `kill -9`, OOM, laptop lid closed — everything is lost. The conversation history, the tool results, the partial progress: all gone.

For a quick question, that's fine. But real coding agents run multi-step tasks that take minutes. If a 15-minute run dies at minute 14, you just wasted 14 minutes of compute and API spend. Worse: the model might have already written half a file, and now you have inconsistent state.

The fix is **checkpointing**: after every significant step (tool call completed, model response received), persist the state. When you restart, pick up exactly where you left off.

### Why this isn't just "save to disk"

Naive checkpointing saves everything. Smart checkpointing saves *just enough* to resume without re-executing. The key insight from DecodingAI's durable runtime:

- **Don't checkpoint the model's internal state** — you can't; it's stateless
- **Do checkpoint the conversation history** — that's what the model needs to continue
- **Do checkpoint tool results** — so you never re-execute a tool that already ran
- **Mark completed steps** — so the resume path knows where to start

## Architecture

```
                     Normal Flow
                    ┌──────────┐
  User prompt ──▶   │ Agent    │ ──▶ Answer
                    │ Loop     │
                    └────┬─────┘
                         │
                    ┌────▼─────┐
                    │Checkpoint│ ──▶ session.jsonl
                    │  Writer  │     (append-only)
                    └──────────┘

                     Resume Flow
                    ┌──────────┐
  session.jsonl ──▶ │Checkpoint│ ──▶ Rebuilt history
                    │  Reader  │     + last step index
                    └────┬─────┘
                         │
                    ┌────▼─────┐
                    │ Agent    │ ──▶ Continue from
                    │ Loop     │     where we stopped
                    └──────────┘
```

## Code Walkthrough

### `checkpoint.py` — The checkpoint system

The checkpoint system uses an **append-only JSONL file** (one JSON object per line). Each line records one event:
- `user_message` — the user's input
- `tool_call` — what the model wanted to call
- `tool_result` — what the tool returned
- `assistant_response` — the model's final answer
- `step_complete` — marks a logical step as done

On resume, we replay the JSONL to rebuild the conversation history without re-executing any tools.

### `crash_simulation.py` — Intentionally crash and recover

This script:
1. Starts a multi-step agent task
2. Simulates a crash mid-way (`kill -9` style)
3. Resumes from the checkpoint
4. Shows that no tool calls are repeated

### `durable_runtime.py` — The full durable wrapper

Wraps the Week 1 agent loop with checkpoint write-through. Every tool call result is persisted before the loop continues.

## Key Design Decisions

### Why JSONL and not SQLite?
JSONL is append-only, human-readable, and trivially diff-able. You can `cat` a session file and see exactly what happened. SQLite is better for querying, but we're not querying — we're replaying. This decision mirrors DecodingAI's choice.

### Why not checkpoint model state?
LLMs are stateless function calls. The model doesn't have "state" to save — it reconstructs context from the conversation history every call. So we checkpoint the history, not the model.

### What about partial file writes?
If the agent wrote half a file before crashing, the checkpoint records the write as completed. On resume, the model sees the write result in history and knows that step is done. It doesn't re-write.

---

## Run It

```bash
cd week-02-resumability-checkpoints/code

# Normal run — watch it checkpoint each step
python durable_runtime.py

# Crash simulation — see the resume in action
python crash_simulation.py
```

## Exercises

See [exercises/exercises.md](exercises/exercises.md)

## References

- [DecodingAI Lesson 3 — Durable Runtime](../../building-a-coding-agent-from-scratch-course/lessons/03-durable-runtime/) — `kill -9` resume, durable HITL waits, what-if replay
- [DecodingAI runtime.md](../../building-a-coding-agent-from-scratch-course/running_the_code/runtime.md) — headless runs and durable checkpoints

---

**Deliverable:** An agent that survives a crash and resumes cleanly.
