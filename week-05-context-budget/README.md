# Week 5 — Context as a Budget (with NOOA Case Study)

> Treat the context window as a finite resource. Memory strategies, compaction, skills injection, LSP-assisted context. NOOA case study: why avoiding compaction can itself be a winning design choice.

---

## Learning Objectives

By the end of this week, you will:
1. Understand the context window as a **finite budget**, not unlimited storage
2. Implement **memory strategies** — AGENTS.md, MEMORY.md, conversation compaction
3. Add **skills injection** — curated domain knowledge loaded on demand
4. Use **LSP-assisted context** — let the language server tell you what's relevant
5. Analyze NVIDIA's **NOOA approach** — why they skip compaction entirely and still win

## The Big Idea

Your agent has been running fine on short tasks. But give it a 30-step task, and something breaks: the model starts forgetting earlier context, repeating itself, or hallucinating file contents it read 20 steps ago.

The problem is the **context window** — the fixed-size buffer of text the model can see at once. Every message, every tool result, every system prompt instruction competes for space in this buffer. When it fills up, you have three options:

1. **Fail** — the run crashes or goes off the rails (unacceptable)
2. **Compact** — summarize older messages to free up space (what most agents do)
3. **Be strategic** — put less in the context in the first place (what NOOA does)

This week you'll implement option 2 (compaction) and learn why option 3 (NOOA's approach) is surprisingly competitive.

## Context Budget Architecture

```
┌─────────────────────── Context Window ───────────────────────┐
│                                                               │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────────┐   │
│  │ System Prompt │  │ Memory/Skills │  │ Conversation     │   │
│  │ (~500 tokens) │  │ (~2k tokens)  │  │ History          │   │
│  │ - Role        │  │ - AGENTS.md   │  │ (variable,       │   │
│  │ - Rules       │  │ - MEMORY.md   │  │  grows each turn)│   │
│  │ - Tool defs   │  │ - Active skill│  │                  │   │
│  └──────────────┘  └───────────────┘  └──────────────────┘   │
│                                                               │
│  Total: ███████████████████░░░░░ 80% used                     │
│                   ▲                                           │
│                   └── Compaction fires here!                  │
└───────────────────────────────────────────────────────────────┘
```

## NOOA Case Study

NVIDIA's NOOA harness takes a fundamentally different approach:

| Traditional Agents | NOOA Approach |
|---|---|
| Fill the context, then compact | Keep context small from the start |
| Summarize old messages | Use method boundaries as natural resets |
| Conversation grows unbounded | Each method call is a fresh context |
| Complex compaction logic | `TokenBudgetSummarizer` compresses between methods |

**Why NOOA's approach works:**
- **Method boundaries are natural compaction points.** When a method completes, its detailed history can be summarized without losing information.
- **Type annotations reduce prompt bloat.** Instead of describing inputs/outputs in the system prompt, NOOA uses Python type hints — the model sees the structure, not a paragraph of explanation.
- **Code-as-action avoids tool schema overhead.** Instead of separate tool definitions, NOOA exposes Python methods directly — fewer tokens spent on schema.

**The result:** NOOA matches or beats other harnesses at roughly half the tokens, and never compacts context at all during a method call.

## Code Walkthrough

### `context_budget.py` — Track and visualize context usage

Monitors how much of the context window is used and triggers compaction at a threshold (default: 80%).

### `memory_strategies.py` — AGENTS.md, MEMORY.md, and skills

Three memory mechanisms:
- **AGENTS.md** — project-specific instructions loaded at session start
- **MEMORY.md** — things the agent learned during previous sessions
- **Skills** — curated domain knowledge loaded on demand

### `lsp_context.py` — LSP-assisted context

Instead of reading entire files, use the Language Server Protocol to get:
- Symbol definitions and references
- Type information
- Only the relevant parts of a file

### `nooa_comparison.py` — Compare your approach against NOOA's

Run the same task with:
1. Your compaction-based approach (compact at 80%)
2. A NOOA-style method-boundary approach (fresh context per subtask)

Compare: total tokens used, answer quality, number of compaction events.

---

## Run It

```bash
cd week-05-context-budget/code

# See context budget in action
python context_budget.py

# Memory strategies demo
python memory_strategies.py

# NOOA comparison
python nooa_comparison.py
```

## Exercises

See [exercises/exercises.md](exercises/exercises.md)

## References

- [DecodingAI Lesson 4 — Context Engineering](../../building-a-coding-agent-from-scratch-course/lessons/04-context-engineering/)
- [NOOA Context Blocks](../../labs-OO-Agents/examples/README.md#step-8-context-blocks) — Context as a first-class API
- [NOOA Summarization](../../labs-OO-Agents/examples/README.md#step-9-automatic-history-summarization) — TokenBudgetSummarizer
- [NOOA Paper](https://arxiv.org/abs/2607.20709) — Published results on token efficiency

---

**Deliverable:** A context-budget report comparing your own techniques against the NOOA approach on a real task.
