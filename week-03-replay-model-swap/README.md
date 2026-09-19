# Week 3 — Replay & Model-Swap Experiments

> Replay history from any point in a run. Swap the underlying model mid-replay ("what would model X have done here?").

---

## Learning Objectives

By the end of this week, you will:
1. Build a **replay harness** that re-executes from any checkpoint
2. **Swap the model** at any point to compare behavior
3. Generate **side-by-side comparison reports** across models
4. Understand replay as a **debugging and evaluation tool**

## The Big Idea

In Week 2, you built checkpoints so a crashed agent can resume. But checkpoints enable something much more powerful: **replay**.

Replay means taking a checkpoint from the middle of a run and re-executing from that point — but with something changed. The most useful change: **swap the model**.

"My agent made a weird choice on step 5. What would Claude have done instead? What about Gemini? What about the same model with a different temperature?"

This isn't hypothetical — this is how you debug agents. You don't stare at logs. You replay the exact scenario with a different model and compare the output.

## Architecture

```
    Original run              Replay branch
    ┌──────────┐              ┌──────────┐
    │ Step 1 ✓ │              │ Step 1 ✓ │ (from checkpoint)
    │ Step 2 ✓ │              │ Step 2 ✓ │ (from checkpoint)
    │ Step 3 ✓ │   ──fork──▶  │ Step 3'  │ ◀── Different model!
    │ Step 4 ✓ │              │ Step 4'  │     Different choices!
    │ Step 5 ✓ │              │ Step 5'  │
    └──────────┘              └──────────┘

    Compare: token cost, tool calls made, final answer quality
```

## Code Walkthrough

### `replay_harness.py` — Fork a run from any checkpoint

The replay harness:
1. Loads a checkpoint up to step N
2. Rebuilds the conversation history
3. Continues execution with the same (or different) model
4. Logs everything to a new checkpoint file

### `model_swap.py` — Swap models and compare

Runs the same task with multiple models from the same starting point:
- Same inherited prompt and observations, same tool schemas
- Different models → different tool calls, token costs, and answers
- Outputs a comparison table

### `comparison_report.py` — Generate a report

Compares two or more replay runs on:
- **Token cost** — which model is cheapest?
- **Tool call count** — which model is most efficient?
- **Answer quality** — side-by-side output for human review
- **Time to completion** — wall-clock time

## Key Design Decisions

### Why replay from checkpoints, not re-execute from scratch?
Because the interesting question is "what would happen from *this exact point*" — not "what would happen with a different first message." Replay lets you isolate exactly where two models diverge.

### Why is this a debugging tool?
When an agent produces a wrong answer, the question is *where* it went wrong. Replay lets you bisect: replay from step 1, step 2, step 3... and find the exact step where the model made a bad choice.

---

## Run It

```bash
cd week-03-replay-model-swap/code

# First, generate a run to replay from
python replay_harness.py --task "List the files in this project and explain the layout"

# Fork the exact same checkpoint prefix once per model
python model_swap.py --original sessions/latest --from-step 1 \
  --models gemini-2.0-flash gpt-4o-mini

# Generate a comparison
python comparison_report.py --runs sessions/swap-* --output comparison_report.md
```

Each session contains an append-only `checkpoint.jsonl` log and a
`run_metrics.json` summary. A replay branch copies its inherited event prefix,
then appends a `replay_metadata` event and only its own new decisions. This
makes the branch independently reproducible while preserving the source run.

`--from-step 0` forks immediately after the user request. Higher values fork
after that many completed tool calls. The harness rejects a step that does not
exist rather than silently replaying the wrong state.

> **Safety boundary:** This Week 3 replay runner reuses the introductory host
> tool executor so its live examples are not a sandbox or permission system.
> Run it only in a disposable workspace. Week 4 adds the containment boundary;
> a production replay runner should inject that executor rather than execute
> tools directly on the host.

## Test It

The unit tests use local fixture checkpoints and do not call a model API:

```bash
python -m unittest discover -s week-03-replay-model-swap/tests -v
```

## Exercises

See [exercises/exercises.md](exercises/exercises.md)

## References

- [DecodingAI Lesson 3 — Durable Runtime](../../building-a-coding-agent-from-scratch-course/lessons/03-durable-runtime/) — what-if replay with model swapped
- [DecodingAI runtime.md](../../building-a-coding-agent-from-scratch-course/running_the_code/runtime.md) — replay commands

---

**Deliverable:** A replay harness usable for debugging and model comparison.
