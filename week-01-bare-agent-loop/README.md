# Week 1 — The Bare Agent Loop

> Build one full user turn end-to-end: prompt → tool call → streamed answer.
> Add a y/n permission gate on every tool call.

---

## Learning Objectives

By the end of this week, you will:
1. Understand the **ReAct pattern** — Reason → Act → Observe → Repeat
2. Build a **minimal agent loop** that calls tools and returns answers
3. Implement a **human-in-the-loop permission gate** on every tool call
4. Know why the **harness, not the model**, decides agent quality

## The Big Idea

Here's the uncomfortable truth about coding agents: **the agent loop itself is about 20 lines of code.** The model receives a prompt, decides to call a tool (or answer directly), you execute the tool, feed the result back, and repeat. That's it.

So what makes Claude Code, Codex, or Cursor *good*? It's not the model — it's everything *around* the loop: the permission system, the sandbox, the context management, the memory. That's the **harness**, and that's what this entire course builds.

But first, we need the loop.

## Architecture

```
┌─────────────────────────────────────────────────┐
│                    HARNESS                       │
│                                                  │
│  ┌──────────┐    ┌──────────┐    ┌───────────┐  │
│  │  Prompt   │───▶│  Model   │───▶│  Parser   │  │
│  │ Assembly  │    │  (LLM)   │    │           │  │
│  └──────────┘    └──────────┘    └─────┬─────┘  │
│       ▲                                │         │
│       │                          ┌─────▼─────┐  │
│       │                          │ Tool Call? │  │
│       │                          └─────┬─────┘  │
│       │                    Yes ┌───────┴──────┐  │
│       │                        │ Permission   │  │
│       │                        │    Gate      │  │
│       │                        │  (y/n)       │  │
│       │                        └───────┬──────┘  │
│       │                                │         │
│       │                        ┌───────▼──────┐  │
│       │                        │   Execute    │  │
│       │                        │    Tool      │  │
│       │                        └───────┬──────┘  │
│       │                                │         │
│       └────────────────────────────────┘         │
│                                                  │
│  No tool call? ──▶ Stream final answer           │
└─────────────────────────────────────────────────┘
```

## The ReAct Pattern

The agent follows a **ReAct** (Reasoning + Acting) loop:

1. **Reason**: The model thinks about what to do next
2. **Act**: It calls a tool (read a file, run a command, write code)
3. **Observe**: It sees the tool's output
4. **Repeat**: Back to step 1, or answer if done

This is the same pattern behind Claude Code, Cursor, and every serious coding agent. The difference is what surrounds it.

## Code Walkthrough

### `agent.py` — The complete agent loop

This is the core. Read it carefully — you'll be surprised how short it is.

The agent loop:
1. Assembles the conversation (system prompt + history + user message)
2. Sends it to the model
3. If the model wants to call a tool → asks permission → executes → loops
4. If the model gives a final answer → done

### `tools.py` — The tools the agent can use

We start with three basic tools:
- `read_file` — Read a file's contents (low risk, auto-approved in Week 4)
- `write_file` — Write content to a file (needs approval)
- `bash` — Run a shell command (needs approval)

Each tool is a plain Python function with a docstring the model can read.

### `permission_gate.py` — The human-in-the-loop gate

Before *any* tool executes, we show the user what the agent wants to do and ask `y/n`. This is the simplest possible safety mechanism, and it's already more than most tutorials teach.

## Key Design Decisions

### Why not use an agent framework?
Because frameworks hide the decisions. You can always *use* LangChain or CrewAI later — but if you don't understand what's underneath, you can't debug, customize, or optimize. Build it once from scratch; use a framework for the rest of your career.

### Why y/n on every tool call?
Because an agent with unrestricted tool access is an agent that can `rm -rf /`. The permission gate is the *first* harness component. In Week 4, we'll build four permission modes with graduated trust.

### Why stream the answer?
Because users need feedback. A 10-second silence followed by a wall of text feels broken. Streaming token-by-token feels responsive and lets the user interrupt.

---

## Run It

```bash
cd week-01-bare-agent-loop/code
python agent.py
```

You'll get an interactive prompt. Try:
- `What files are in the current directory?` (triggers `bash` with `ls`)
- `Read the README.md file` (triggers `read_file`)
- `Create a file called hello.txt with "Hello from my agent"` (triggers `write_file` — asks permission!)

## Exercises

See [exercises/exercises.md](exercises/exercises.md) for hands-on practice.

## References

### From the reference repos
- [DecodingAI Lesson 1 — System Design](../../building-a-coding-agent-from-scratch-course/lessons/01-system-design/) — the harness-vs-loop-vs-model framing
- [DecodingAI Lesson 2 — Agent Loop](../../building-a-coding-agent-from-scratch-course/lessons/02-agent-loop/) — ReAct turn, tool gate, and steering

### Key articles
| Article | Why read it |
|---|---|
| [The Anatomy of an Agent Harness](https://www.langchain.com/blog/the-anatomy-of-an-agent-harness) | The experiment that proves the harness matters more than the model |
| [Tool Calling From Scratch to Production](https://www.decodingai.com/p/tool-calling-from-scratch-to-production) | The 5-step tool loop dissected |
| [Building Production ReAct Agents](https://www.decodingai.com/p/building-production-react-agents) | A production ReAct loop from source |

---

**Deliverable:** A working single-turn agent with human-in-the-loop approval on every tool call.
