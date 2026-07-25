# Building a Coding Agent From Scratch

**The harness — not the model — is what makes an agent good.**
Same model, different harness, can swing results by double digits and token cost even more.
This course proves that claim hands-on, then backs it with NVIDIA's own NOOA research.

---

## Course Format

| | |
|---|---|
| **Format** | Recorded core lessons + weekly live session + cohort group |
| **Duration** | 8 weeks |
| **Level** | Intermediate Python — beginner LLM/agent knowledge is fine |
| **Cost to run** | $0 on free tiers (Gemini API, OpenRouter `:free` models) |

## What You'll Build

By the end of this course you'll have built a working coding agent from scratch — not a wrapper around someone else's framework, but your own agent with:

- A **ReAct agent loop** with human-in-the-loop approval on every tool call
- **Durable checkpoints** that survive `kill -9` and resume without re-paying for finished work
- A **replay harness** for debugging and model comparison ("what would GPT have done here?")
- **Four permission modes** and **Docker/remote sandboxing** for safe execution
- **Context budget management** — memory, compaction, skills injection, LSP
- The **agent-as-Python-object** pattern from NVIDIA's NOOA research
- **Parallel subagent fan-out** with per-child budgets and structured reports
- **Evaluation infrastructure** — benchmarks, regression probes, and online evals

## Core Thesis

In [one public experiment by LangChain](https://www.langchain.com/blog/the-anatomy-of-an-agent-harness), changing only the *harness* — same model throughout — moved a coding agent from roughly 30th place into the top 5 on Terminal-Bench. The harness decides what the model sees, what it touches, and what happens when it's wrong. **It's also the part nobody teaches.**

This course teaches it.

---

## Course Outline

| Week | Topic | Deliverable |
|---|---|---|
| **1** | [The Bare Agent Loop](week-01-bare-agent-loop/) | Working single-turn agent with human-in-the-loop approval |
| **2** | [Resumability & Checkpoints](week-02-resumability-checkpoints/) | Agent that survives a crash and resumes cleanly |
| **3** | [Replay & Model-Swap Experiments](week-03-replay-model-swap/) | Replay harness for debugging and model comparison |
| **4** | [Containment & Sandboxing](week-04-containment-sandboxing/) | Agent running safely in an isolated, remote environment |
| **5** | [Context as a Budget](week-05-context-budget/) | Context-budget report comparing techniques against NOOA's approach |
| **6** | [Harness Design as the Real Lever](week-06-harness-design/) | Refactored agent using the "agent as Python object" pattern, benchmarked |
| **7** | [Parallel Subagents](week-07-parallel-subagents/) | Working subagent swarm with honest single-agent comparison |
| **8** | [Evaluation & Real-World Swarms](week-08-evaluation-real-world/) | Agent that closes a real GitHub issue, benchmarked and documented |

## Prerequisites

| Category | Requirements |
|----------|-------------|
| **Python** | Intermediate — you can read classes, async/await, and decorators |
| **LLMs** | Beginner — you know what a prompt is and have used ChatGPT |
| **Hardware** | Modern laptop/PC. Docker optional (for local sandbox); heavier work runs in the cloud |
| **API Keys** | Gemini API (free tier) or OpenRouter (free models) |

## Quick Start

```bash
git clone <repo-url>
cd coding-agent-course
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # add your API key
cd week-01-bare-agent-loop/code
python agent.py
```

## Project Structure

```
coding-agent-course/
├── README.md                  # You are here
├── requirements.txt           # Base Python dependencies
├── .env.example               # API key template
├── shared/                    # Shared utilities across all weeks
│   ├── config.py              # Configuration & API key loading
│   ├── models.py              # Model provider abstraction
│   └── utils.py               # Common helpers
├── week-01-bare-agent-loop/
│   ├── README.md              # Lesson narrative
│   ├── code/                  # Runnable Python files
│   ├── exercises/             # Hands-on exercises
│   └── references/            # Source links & deeper dives
├── week-02-resumability-checkpoints/
│   └── ...
├── ...
└── week-08-evaluation-real-world/
    └── ...
```

## Reference Material

This course draws on and credits these excellent open-source resources:

| Resource | Used For |
|---|---|
| [Building a Coding Agent From Scratch](https://github.com/decodingai-magazine/building-a-coding-agent-from-scratch-course) by DecodingAI | Agent loop architecture, tools, permissions, sandboxing, evals |
| [NVIDIA OO Agents (NOOA)](https://github.com/NVIDIA-NeMo/labs-OO-Agents) | Agent-as-Python-object pattern, context engineering, harness design |
| [NOOA Paper](https://arxiv.org/abs/2607.20709) | Published benchmark results & design principles |

## How Each Lesson Works

1. **Watch the system in action** — see the working feature before you understand the code
2. **Extract the principle** — understand *why* this design decision was made
3. **Build it yourself** — write the code from scratch in your own agent
4. **Exercise it** — push the system with exercises designed to break and strengthen your understanding

---

## License

Apache-2.0 — clone, fork, and build on it.
