# Building a Coding Agent From Scratch, Week 6: The Harness Is the Product

### The model can choose a tool call in a few lines. Everything that makes the result reliable, inspectable, and safe lives around those lines.

The coding-agent loop is famously small. Give a model tools, send it a prompt, execute the calls it returns, feed the results back, and stop when it produces an answer.

```python
async with agent.iter(prompt, message_history=history) as run:
    async for node in run:
        stream_events(node)
```

That is the agent loop. It is not the coding agent product.

After five weeks of building durability, replay, containment, and context management, this distinction has become the main lesson of the series. A model can decide to call `bash`. The harness decides whether the call waits for approval, where it executes, what it can read, how its output is truncated, how the event is persisted, whether a user can steer the next decision, and how we know a later refactor did not break any of that.

The harness is the product.

For this article, I am using the canonical [`decode`](https://github.com/silsgah/building-a-coding-agent-from-scratch-course) implementation as the standard: its [system-design lesson](https://github.com/silsgah/building-a-coding-agent-from-scratch-course/tree/master/lessons/01-system-design), architecture decision records, runnable surfaces, and test suite. The smaller companion Week 6 code is a learning exercise; it is not a second competing product.

## Series navigation

- [Week 1 — Why the Agent Loop is 20 Lines of Code](https://kwablagah.substack.com/p/why-the-agent-loop-is-20-lines-of?r=bpg99)
- [Week 2 — Your Coding Agent Has a Fatal Flaw](https://kwablagah.substack.com/p/your-coding-agent-has-a-fatal-flaw?r=bpg99)
- [Week 3 — Replay Is an Experiment, Not a Rerun](https://github.com/silsgah/coding-agent-course/tree/master/week-03-replay-model-swap)
- [Week 4 — Permission Is Not Containment](https://github.com/silsgah/coding-agent-course/tree/master/week-04-containment-sandboxing)
- [Week 5 — Context Is a Budget, Not a Memory Dump](https://github.com/silsgah/coding-agent-course/tree/master/week-05-context-budget)
- **Week 6 — The Harness Is the Product**
- Next: **Week 7 — Parallelism Is a Coordination Problem**

## What belongs inside the harness

The most useful definition is practical: the harness is every piece of software that turns a general-purpose model into a particular coding agent.

```text
                     ┌──────────────────────────────┐
                     │           Harness            │
user ──► interface ─►│ turn lifecycle and queues     │
                     │ permission gate               │
                     │ tool registry and executor    │──► filesystem / shell / web
                     │ context, memory, skills       │
                     │ persistence and replay        │
                     │ tracing, tests, and evals     │
                     └──────────────┬───────────────┘
                                    model
```

The model is important, but it is only one dependency in that diagram. Swap it for a stronger model and the agent can still be unsafe, forgetful, unauditable, or impossible to reproduce. Keep the model fixed and improve the harness, and the agent can become dramatically more useful.

This framing prevents a common mistake: treating prompts as the architecture. A system prompt can explain a policy, but it cannot enforce one. A model can be told to stay in the project directory, but only the executor and workspace boundary can restrict its filesystem. A model can be instructed to remember decisions, but only persistence and context design control what survives a crash or fits in the next request.

## One headless core, two ways to drive it

`decode` has two user-facing modes with a shared agent core:

| Surface | Optimized for | What the harness adds |
| --- | --- | --- |
| Interactive terminal UI | Collaboration with a human | Streaming output, approvals, steering, follow-ups, context visibility. |
| Headless runtime | Long-running and repeatable execution | Durable checkpoints, resume, named replay anchors, and operational inspection. |

This is an architectural choice, not a cosmetic one. A terminal UI should feel responsive and permit a person to guide work in progress. A headless run needs a stable execution identity, durable state, and a way to recover after the process that launched it is gone.

The two modes should not become two agents. They should share the loop, tools, permissions, provider construction, and workspace semantics. Otherwise a fix in one path becomes a silent regression in the other, and “works in the demo” stops meaning anything useful.

## A turn is a lifecycle, not one model request

In a toy script, a turn begins at the prompt and ends at a final answer. In an interactive coding agent, a turn can contain multiple model requests, tool calls, user approvals, questions, and steering messages.

The key design is to make those boundaries explicit.

```text
prompt
  │
  ▼
model streams text and proposes tools
  │
  ▼
permission / ask-user boundary ──► human decision or answer
  │                                      ▲
  ├── drain steering messages ───────────┘
  ▼
execute allowed tools
  │
  ▼
next model-request leg ──► final answer or another boundary
```

The canonical harness uses deferred tool requests for that boundary. Instead of executing a model-selected tool immediately, it pauses, asks the permission gate for an allow/ask/deny decision, gathers any human input, then resumes the loop with the result.

That single mechanism buys two properties at once:

1. A sensitive tool does not execute before approval.
2. A user’s steering input can be injected before the next model request, without trying to interrupt a tool or streaming response in the middle of execution.

The constraint is honest: steering is cooperative, not telepathy. The user can redirect the agent at a well-defined boundary; they cannot retroactively change a command that is already running. Making that visible in the turn lifecycle is far safer than pretending an interface can interrupt anything at any time.

## Queues encode product behavior

One subtle example shows why the harness deserves normal software design. While an agent is working, a user can mean two different things by sending another message:

- “Consider this before you make your next decision.”
- “Finish the current task, then start this new task.”

The canonical design represents these meanings with separate queues. A **steering** queue is drained before the next model-request leg. A **follow-up** queue waits until the current turn would otherwise stop. A single-flight lock spans the entire multi-leg turn, so two partially overlapping turns cannot mutate the same history and tool state concurrently.

That is not an LLM trick. It is ordinary concurrency design applied to an agent UI. It turns a vague chat experience into predictable behavior a user can learn and a test suite can verify.

## Tools should be contracts, not prompt suggestions

A tool surface is an API. It needs a name, argument schema, description, execution behavior, permissions, result rendering, and tests. The agent sees the description; the runtime sees the contract.

The core coding tools make this concrete:

- **File tools** paginate reads, constrain writes and edits, normalize text where needed, and return controlled failures instead of vague exceptions.
- **`bash`** has timeout and output limits behind an executor seam, so the same tool contract can run locally, in Docker, or in a remote sandbox.
- **Web fetch** fetches and converts content into a narrower form before it enters model context; it remains a separately gated host-side capability.
- **Tasks and ask-user tools** express harness state and deferred interaction rather than pretending every need is a shell command.

The important abstraction is not “make everything pluggable.” It is to locate a seam at the actual source of variation. The command executor is a good seam because the rest of the agent should not care whether `bash` runs in a host process, Docker workspace, or remote sandbox. A separate abstraction for every function would hide behavior without buying flexibility.

## State has to be visible and durable

A capable agent accumulates state: message history, permission decisions, tool outputs, the current workspace, task lists, selected skills, memory, execution identifiers, and metrics. If that state exists only inside a process, crashes turn ordinary work into forensic guesswork.

The harness makes these artifacts inspectable:

```text
.decode/
├── sessions/       append-only conversation and compaction records
├── MEMORY.md       compact cross-session knowledge
├── skills/         task-specific operating procedures
├── settings.json   deterministic user/project policy
└── logs/           operational diagnostics
```

The exact storage mechanism changes with the operating mode. The interactive path keeps replayable session records. The headless runtime adds durable workflow checkpoints and named replay anchors. What should not change is the principle: an operator must be able to inspect what the agent knew, what it did, and where it is safe to resume.

Visible state is also a review tool. When a user asks why an agent behaved a certain way, “the model decided” is not enough. The harness should let us inspect the input context, tool results, gate decisions, durable events, and downstream side effects.

## Configuration is a security boundary

Agent configuration is often treated as convenience: which provider, which model, which timeout. In a coding agent it also controls authority.

The selected sandbox mode answers where arbitrary computation runs. Permission mode and rules decide which calls need human approval. The repository setting establishes the workspace source. Environment selection controls how secrets enter the harness. Context settings decide when a long conversation is trimmed or summarized.

These controls need one readable, typed configuration surface with clear defaults and startup guards. A request to use Docker with no reachable daemon should fail before an agent starts, rather than quietly falling back to the host. A remote environment missing its configuration should fail loudly, rather than borrowing a developer’s local `.env` by accident.

The philosophy is consistent: make unsafe or ambiguous configurations unrepresentable where possible, and obvious where they are not.

## Architecture decisions are product documentation

The canonical project uses Architecture Decision Records (ADRs) to preserve the reasoning behind non-obvious choices: why tool approval uses a deferred boundary, why sessions use append-only records, why compaction has two tiers, why the workspace is isolated, and why a credential proxy was later removed rather than defended indefinitely.

An ADR is not ceremony for its own sake. It records the context, decision, alternatives, consequences, and later amendments. That matters in an agent project because the tempting implementation is often locally plausible but globally wrong. For example:

- Running `bash` in a container while file tools still touch the host creates a split, untruthful workspace.
- Caching side-effecting shell output during replay is fast but incorrect.
- Silently falling back from a remote or container executor to the host invalidates the safety claim.
- Shrinking history without a durable checkpoint makes a resumed run reason from different state.

The code tells us what happens now. The ADR explains why this particular seam, invariant, or trade-off exists—and what must remain true when it changes.

## Test the seams, then test the vertical slice

The right test strategy follows the architecture.

Unit tests exercise deterministic contracts: permission decisions, path containment, tool rendering, queue behavior, context triggers, settings validation, and serialization. They use scripted models or fakes rather than turning a provider API into a test dependency.

Integration capstones exercise the real composition: a gated tool call through the agent loop, a durable runtime execution, a sandbox workspace, a compaction/resume path, or a parallel fan-out. They replace only the genuinely external boundary—such as a model or sandbox backend—while keeping the production seam intact.

This produces better evidence than a screenshot of a successful terminal session. A happy-path demo can show that a system once worked. A capstone can show that the claimed interaction between components still works after many changes.

Evaluation is a third layer, not a substitute for either. Tests prove specified mechanisms. Evals assess whether the resulting agent completes representative work. The distinction becomes central in Week 8.

## The larger lesson

It is tempting to describe agent engineering as prompt engineering with tools attached. That sells the hard part short.

The hard part is the surrounding system: one coherent turn lifecycle, a clear human-control model, deterministic policy, tool contracts, bounded execution, durable evidence, context discipline, configuration that fails safely, and tests that make each claim checkable.

That is the harness. It is where an agent earns the right to be trusted with a repository.

Next, I will extend the harness from one controlled worker to several: parallelism can accelerate independent research, but it also multiplies context, authority, cost, and coordination mistakes unless the parent-child contract is designed just as carefully.

---

*This is Week 6 of my “Building a Coding Agent From Scratch” series. Read the [canonical system-design lesson](https://github.com/silsgah/building-a-coding-agent-from-scratch-course/tree/master/lessons/01-system-design) and explore the [companion Week 6 lab](https://github.com/silsgah/coding-agent-course/tree/master/week-06-harness-design).*
