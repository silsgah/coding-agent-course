<div align="center">

# 🛠️ Building a Coding Agent From Scratch

### The harness — not the model — makes a coding agent good. Build one from scratch, week by week, and prove it.

<br>

![Course](https://img.shields.io/badge/type-cohort_course-8a2be2)
![Weeks](https://img.shields.io/badge/duration-8_weeks-blue)
![Cost](https://img.shields.io/badge/cost_to_run-$0-2ea44f)
![Code](https://img.shields.io/badge/code-from_scratch-orange)
![License](https://img.shields.io/badge/license-Apache--2.0-lightgrey)

</div>

---

> **Try it in 5 minutes, $0:**
>
> ```bash
> git clone <repo-url>
> cd coding-agent-course
> python -m venv .venv && source .venv/bin/activate
> pip install -r requirements.txt
> cp .env.example .env   # set GEMINI_API_KEY — free at https://aistudio.google.com/apikey
> cd week-01-bare-agent-loop/code
> python agent.py
> ```
>
> Then type `What files are in the current directory?` and watch the agent loop in action — prompt → tool call → permission gate → answer.

---

## 📖 About This Course

In [one public experiment by LangChain](https://www.langchain.com/blog/the-anatomy-of-an-agent-harness), changing only the *harness* — same model throughout — moved a coding agent from roughly 30th place into the top 5 on Terminal-Bench. The harness decides what the model sees, what it touches, and what happens when it's wrong. It's also the part nobody teaches.

### The agent is ~20 lines. The course is everything else.

```python
# The entire tool-calling agent loop:
messages = [system_prompt] + history + [user_message]

for iteration in range(max_iterations):
    response = await provider.chat(messages, tools=TOOL_SCHEMAS)

    if response.tool_calls:
        for tool_call in response.tool_calls:
            if ask_permission(tool_call):          # ← harness
                result = execute_tool(tool_call)   # ← harness
            messages.append(tool_result)
        continue

    return response.content  # Done.
```

That's the *entire* agent loop — the thing people call "the agent" ends here. Everything else — the permission gate, the checkpoint system, the sandbox, context compaction, the replay harness, the subagent fan-out, the evaluation suite — is the **harness**. That's what you're here to build.

We spent months studying Claude Code (via its leaked source), [OpenCode](https://github.com/anomalyco/opencode), [Aider](https://github.com/aider-ai/aider), and NVIDIA's [OO Agents (NOOA)](https://github.com/NVIDIA-NeMo/labs-OO-Agents), then distilled it into 8 weeks where, from an empty repo, you build your own terminal coding agent. By Week 2 it survives `kill -9`; by Week 4 it runs in a Docker sandbox; by Week 7 it's running 5 agents in parallel; by Week 8 it's closing real GitHub issues.

**You walk away with three things:**

1. **The skill behind that leaderboard jump** — engineering custom harnesses for your own AI products.
2. **No more magic** — nothing Claude Code or Codex does is a mystery once you've built the code underneath.
3. **A working agent** — point your agent at your own repos the way you point Claude Code at them today.

---

## 🎯 What You'll Build, Week by Week

By the end of this course you'll have built a working coding agent from scratch — not a wrapper around someone else's framework, but your own agent with all the harness components that make production agents work:

| Component | What It Does | Week |
|-----------|-------------|------|
| 🔄 **ReAct Agent Loop** | prompt → model → tool call → answer, with streamed output | 1 |
| 🔐 **Permission Gate** | y/n approval on every tool call (4 graduated modes) | 1, 4 |
| 💾 **Durable Checkpoints** | Survive `kill -9` and resume without re-paying for finished work | 2 |
| 🔁 **Replay Harness** | Fork from any checkpoint with a different model ("what would GPT do here?") | 3 |
| 🐳 **Docker Sandbox** | Execute tools inside a disposable container — nothing touches your machine | 4 |
| 📊 **Context Budget** | Treat the context window as a finite resource with visual gauges | 5 |
| 🧠 **Memory & Skills** | AGENTS.md, MEMORY.md, and on-demand skill injection | 5 |
| 🏗️ **Agent-as-Object** | NVIDIA NOOA's pattern: methods = tools, docstrings = prompts | 6 |
| 🔀 **Parallel Subagents** | Fan out N children, each with budget + structured report contract | 7 |
| ✅ **Eval Suite** | Benchmarks, regression probes, LLM-as-judge scoring | 8 |
| 🚀 **Issue → PR Pipeline** | GitHub issue in → agent swarm → reviewed pull request out | 8 |

---

## 📚 Course Outline

Eight written lessons, each pairing a narrative README with runnable Python code, hands-on exercises, and reference links.

<table>
  <tr>
    <th align="center">Week</th>
    <th align="center">Topic</th>
    <th align="center">Description</th>
    <th align="center">Key Code</th>
  </tr>
  <tr>
    <td align="center"><b>1</b><br/>The Bare Agent Loop</td>
    <td align="center"><a href="week-01-bare-agent-loop/">📄 Lesson</a></td>
    <td>Build one full user turn end-to-end: prompt → tool call → streamed answer. Add a y/n permission gate on every tool call.</td>
    <td><code>agent.py</code> · <code>tools.py</code> · <code>permission_gate.py</code></td>
  </tr>
  <tr>
    <td align="center"><b>2</b><br/>Resumability & Checkpoints</td>
    <td align="center"><a href="week-02-resumability-checkpoints/">📄 Lesson</a></td>
    <td>Simulate <code>kill -9</code> mid-task. Build checkpointing so a resumed run never re-pays for already-finished work.</td>
    <td><code>checkpoint.py</code> · <code>crash_simulation.py</code> · <code>durable_runtime.py</code></td>
  </tr>
  <tr>
    <td align="center"><b>3</b><br/>Replay & Model-Swap</td>
    <td align="center"><a href="week-03-replay-model-swap/">📄 Lesson</a></td>
    <td>Replay history from any point in a run. Swap the underlying model mid-replay ("what would model X have done here?").</td>
    <td><code>replay_harness.py</code> · <code>model_swap.py</code></td>
  </tr>
  <tr>
    <td align="center"><b>4</b><br/>Containment & Sandboxing</td>
    <td align="center"><a href="week-04-containment-sandboxing/">📄 Lesson</a></td>
    <td>Four permission modes (read-only → full trust). Docker Workspace isolation. Remote sandbox execution.</td>
    <td><code>permission_modes.py</code> · <code>docker_workspace.py</code></td>
  </tr>
  <tr>
    <td align="center"><b>5</b><br/>Context as a Budget</td>
    <td align="center"><a href="week-05-context-budget/">📄 Lesson</a></td>
    <td>Treat the context window as a finite resource. Memory strategies, compaction, skills injection. <b>NOOA case study:</b> why avoiding compaction can itself be a winning design choice.</td>
    <td><code>context_budget.py</code> · <code>memory_strategies.py</code></td>
  </tr>
  <tr>
    <td align="center"><b>6</b><br/>Harness Design (NOOA)</td>
    <td align="center"><a href="week-06-harness-design/">📄 Lesson</a></td>
    <td>NOOA's mental model: an agent as a plain Python object. Methods are tools, docstrings are prompts. Refactor your Week 1–4 agent and benchmark before/after.</td>
    <td><code>agent_as_object.py</code></td>
  </tr>
  <tr>
    <td align="center"><b>7</b><br/>Parallel Subagents</td>
    <td align="center"><a href="week-07-parallel-subagents/">📄 Lesson</a></td>
    <td>Fan out one call into N child agents, each with its own budget and report contract. Compare hand-rolled swarm against NOOA-style single-agent design.</td>
    <td><code>subagent_swarm.py</code></td>
  </tr>
  <tr>
    <td align="center"><b>8</b><br/>Evaluation & Capstone</td>
    <td align="center"><a href="week-08-evaluation-real-world/">📄 Lesson</a></td>
    <td>Build benchmarks, regression probes, and online evals. End-to-end: a GitHub issue → the swarm returns a reviewed pull request.</td>
    <td><code>benchmark_suite.py</code></td>
  </tr>
</table>

---

## 🤖 You'll Walk Away Knowing How To

- **Build one user turn end-to-end** — prompt to streamed answer, with a `y/n` gate on every tool call.
- **`kill -9` a run mid-task and resume it** — checkpoints never re-pay for finished work.
- **Replay history with the model swapped** — "what would `gemini-2.5-pro` have done from this exact point?"
- **Contain the agent** — four permission modes, then a Docker Workspace, then a remote sandbox.
- **Treat the context window as a budget** — memory, compaction, skills; each a measured before/after experiment.
- **Refactor an agent into the NOOA pattern** — methods as tools, docstrings as prompts, tested with `pytest`.
- **Fan out parallel subagents** — one call, N children, each with a budget and a report contract.
- **Evaluate the thing you built** — benchmarks, regression probes, online evals; a green test suite isn't enough.

Every lesson runs the same way: **see the system work first, then extract the underlying principle.**

---

## 👥 Who Should Join?

**For: engineers who learn by building.** You finish with a working coding agent and patterns to steal for your own agentic applications.

| Target Audience | Why Join? |
|-----------------|-----------| 
| **ML/AI Engineers** | Build a complete agentic system — loop, tools, sandbox, evals — not another notebook demo. |
| **Software Engineers** | Stop treating the agent in your terminal as a black box. |
| **AI/Platform Engineers** | The ops half nobody covers: sandboxing, durability, secrets, observability. |
| **Technical Founders** | Understand what your team is building and make better architecture decisions. |

---

## 🎓 Prerequisites

| Category | Requirements |
|----------|-------------|
| **Python** | Intermediate — you can read classes, async/await, and decorators |
| **LLMs & Agents** | Beginner — you know what a prompt is and have used ChatGPT |
| **Hardware** | Modern laptop/PC. Docker optional (for local sandbox in Week 4) |
| **Time** | ~4–6 hours for the whole course — 4 if you read, 6 if you run everything |

---

## 💰 Cost Structure

Running the code costs **$0** if you stick to free tiers:

| Service | Cost |
|---------|------|
| **Gemini API** (default provider) | Free tier — [Google AI Studio](https://aistudio.google.com/apikey) |
| **OpenRouter** (alternative provider) | $0 on `:free` models — [openrouter.ai](https://openrouter.ai) |
| **Docker** (Week 4 sandbox) | Free — [docker.com](https://docker.com) |

**Reading-only? Everything's free!** You can read every lesson and study every code file without running anything.

---

## ⚙️ Quick Start

### 1. Clone and install

```bash
git clone <repo-url>
cd coding-agent-course
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Add your API key

```bash
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY (free at https://aistudio.google.com/apikey)
```

### 3. Run your first agent

```bash
cd week-01-bare-agent-loop/code
python agent.py
```

You'll see an interactive prompt. Try these:
- `What files are in the current directory?` — triggers `bash` with `ls`
- `Read the README.md file` — triggers `read_file`
- `Create a file called hello.txt with "Hello from my agent"` — triggers `write_file` and **asks permission!**

### 4. Work through the weeks

Each week has the same structure:
1. Read the `README.md` lesson — understand the concept and design decisions
2. Run the code in `code/` — see it working
3. Do the exercises in `exercises/` — build understanding through practice
4. Explore `references/` — deeper dives into source material

---

## 🏗️ Project Structure

One Python project; each week maps to one component of the harness architecture:

```
coding-agent-course/
├── README.md                              # ← You are here
├── requirements.txt                       # Base Python dependencies
├── .env.example                           # API key template
│
├── shared/                                # Shared utilities across all weeks
│   ├── __init__.py
│   ├── config.py                          # Configuration & API key loading
│   ├── models.py                          # Model provider abstraction (Gemini, OpenAI, OpenRouter)
│   └── utils.py                           # Pretty printing, session logging, timing
│
├── week-01-bare-agent-loop/               # The ReAct loop + permission gate
│   ├── README.md                          # Lesson: why the harness matters
│   ├── code/
│   │   ├── agent.py                       # The complete agent loop (~150 lines)
│   │   ├── tools.py                       # read_file, write_file, bash
│   │   └── permission_gate.py             # y/n approval with risk levels
│   ├── exercises/exercises.md             # 5 exercises with solutions
│   └── references/sources.md             # DecodingAI articles, source links
│
├── week-02-resumability-checkpoints/      # Crash-safe durable execution
│   ├── README.md                          # Lesson: why durability matters
│   ├── code/
│   │   ├── checkpoint.py                  # Append-only JSONL checkpoint system
│   │   ├── crash_simulation.py            # Crash mid-task and resume demo
│   │   └── durable_runtime.py             # Agent loop with checkpoint write-through
│   ├── exercises/exercises.md
│   └── references/sources.md
│
├── week-03-replay-model-swap/             # Debugging by replaying with different models
│   ├── README.md                          # Lesson: replay as a debugging tool
│   ├── code/
│   │   ├── replay_harness.py              # Fork from any checkpoint step
│   │   └── model_swap.py                  # Same task, multiple models, comparison table
│   ├── exercises/exercises.md
│   └── references/sources.md
│
├── week-04-containment-sandboxing/        # Graduated trust + Docker isolation
│   ├── README.md                          # Lesson: containment is a harness problem
│   ├── code/
│   │   ├── permission_modes.py            # deny-all / ask-all / auto-read / full-trust
│   │   └── docker_workspace.py            # Docker-isolated tool execution
│   ├── exercises/exercises.md
│   └── references/sources.md
│
├── week-05-context-budget/                # Context window management + NOOA case study
│   ├── README.md                          # Lesson: context window as a budget
│   ├── code/
│   │   ├── context_budget.py              # Token tracking, compaction at 80%, visual gauge
│   │   └── memory_strategies.py           # AGENTS.md, MEMORY.md, and Skills injection
│   ├── exercises/exercises.md
│   └── references/sources.md
│
├── week-06-harness-design/                # NOOA: agent-as-Python-object pattern
│   ├── README.md                          # Lesson: the harness IS the lever
│   ├── code/
│   │   └── agent_as_object.py             # Complete agent using NOOA mental model
│   ├── exercises/exercises.md
│   └── references/sources.md
│
├── week-07-parallel-subagents/            # Parallel fan-out with structured reports
│   ├── README.md                          # Lesson: when to swarm, when not to
│   ├── code/
│   │   └── subagent_swarm.py              # Coordinator → N children → merge
│   ├── exercises/exercises.md
│   └── references/sources.md
│
└── week-08-evaluation-real-world/         # Benchmarks, regression, GitHub issue → PR
    ├── README.md                          # Lesson: evaluation infrastructure
    ├── code/
    │   └── benchmark_suite.py             # Repeatable task eval with pass/fail scoring
    ├── exercises/exercises.md             # Capstone project (3 tracks)
    └── references/sources.md
```

---

## 🔬 The Core Thesis — With Evidence

The course is built on a single, testable claim:

> **The same model, wrapped in different harnesses, produces double-digit swings in benchmark results — and even bigger swings in token cost.**

Here's the evidence we examine:

| Evidence | Source | What It Shows |
|----------|--------|---------------|
| LangChain Terminal-Bench experiment | [LangChain Blog](https://www.langchain.com/blog/the-anatomy-of-an-agent-harness) | Same model moved from ~30th to top 5 by changing only the harness |
| NVIDIA NOOA benchmark results | [arXiv:2607.20709](https://arxiv.org/abs/2607.20709) | Competitive SWE-bench results from a genuinely small codebase |
| NOOA token efficiency | NOOA Paper | Matches or beats other harnesses at roughly **half** the tokens |
| Your own experiments | Weeks 3, 5, 6 | You measure this yourself — model-swap, context budget, refactoring |

This isn't a theoretical claim. By Week 6, you'll have your own before/after numbers.

---

## 📋 Reference Material

This course draws on and credits these excellent open-source resources:

| Resource | What It Provides | Used In |
|----------|-----------------|---------|
| [Building a Coding Agent From Scratch](https://github.com/decodingai-magazine/building-a-coding-agent-from-scratch-course) by DecodingAI | Agent loop architecture, tools, permissions, sandboxing, context engineering, evals, remote swarms | Weeks 1–5, 7–8 |
| [NVIDIA OO Agents (NOOA)](https://github.com/NVIDIA-NeMo/labs-OO-Agents) | Agent-as-Python-object pattern, context blocks, skills, summarization, self-extending agents | Weeks 5–7 |
| [NOOA Paper](https://arxiv.org/abs/2607.20709) | Design principles, benchmark methodology, SWE-bench & Terminal-Bench results | Weeks 5–6 |

---

## 📐 How Each Lesson Works

Every lesson follows the same four-step pattern:

```
1. SEE IT WORK          Watch the finished feature in action before
                        you understand the code.

2. EXTRACT THE          Understand WHY this design decision was made.
   PRINCIPLE            What alternatives were rejected? What breaks
                        without it?

3. BUILD IT             Write the code from scratch in your own agent.
   YOURSELF             Not copy-paste — type it, run it, break it.

4. EXERCISE IT          Push the system with exercises designed to
                        break and strengthen your understanding.
```

Each week folder contains:
- **`README.md`** — 2,000–4,000 word lesson narrative with architecture diagrams, code walkthroughs, and design decisions
- **`code/`** — Standalone, runnable Python files (not notebooks — real code)
- **`exercises/`** — 5 hands-on exercises with graduated difficulty and solutions
- **`references/`** — Curated links to source files, articles, and deeper dives

---

## ❓ FAQ

**Do I need a paid API key?**
No. Gemini has a free tier, OpenRouter has free models. See [Cost Structure](#-cost-structure).

**Why Python and not TypeScript or Go?**
Accessibility. Claude Code and OpenCode use TypeScript; Aider proves Python can carry a serious coding agent. The design decisions transfer to any language.

**Why build from scratch instead of using LangChain / CrewAI?**
Because adding custom logic to an existing framework is the easy part — *knowing what to add* requires understanding the internals. Build it once from scratch; use a framework for the rest of your career.

**Why no vector database or codebase index?**
Deliberately. Memory is plain files — `AGENTS.md` for your instructions, `MEMORY.md` for what the agent learns — and the repo is explored just-in-time with grep and LSP. Fresh reads beat a stale index.

**What's the NOOA integration about?**
NVIDIA's [OO Agents framework](https://github.com/NVIDIA-NeMo/labs-OO-Agents) (NOOA) represents a genuinely different approach to agent design: agents as Python objects, methods as tools, docstrings as prompts. Weeks 5–6 use it as a research case study — you compare your harness against theirs and measure the difference.

**How long does the whole course take?**
~4 hours reading-only, ~6 hours if you run everything, ~10+ hours if you do all exercises.

---

## 🤝 Contributing

Found a bug and know the fix? Fork, fix, and open a pull request. Future readers thank you 🤗

---

## License

Released under [Apache-2.0](LICENSE) — clone, fork, and build on it.
