# Building a Coding Agent From Scratch, Week 7: Parallelism Is a Coordination Problem

### A swarm is not “more agents.” It is a contract for dividing work, bounding resources, restricting authority, and returning evidence a parent can use.

The first six weeks of this series made one coding agent more capable and more disciplined. It can use tools, survive interruption, replay decisions, operate inside a workspace boundary, manage its context budget, and expose its behavior through an engineered harness.

This week changes the shape of the work.

Some coding tasks are slow because they contain independent investigations: map the module layout, find the relevant tests, trace a configuration value, and inspect the public API. One agent can do all of that sequentially. It does not have to.

The tempting answer is to spawn several agents. The dangerous answer is to spawn several agents without deciding what they may do, how many may run, what they must return, what gets persisted, and what happens when one produces nonsense.

Parallelism is a coordination problem.

This installment follows the canonical [`decode`](https://github.com/silsgah/building-a-coding-agent-from-scratch-course) implementation and its [subagents lesson](https://github.com/silsgah/building-a-coding-agent-from-scratch-course/tree/master/lessons/06-subagents). Its architecture decision records make the important point explicit: a useful child is not a second unbounded chat session. It is a scoped, read-only exploration loop with a budget and a report contract.

## Series navigation

- [Week 1 — Why the Agent Loop is 20 Lines of Code](https://kwablagah.substack.com/p/why-the-agent-loop-is-20-lines-of?r=bpg99)
- [Week 2 — Your Coding Agent Has a Fatal Flaw](https://kwablagah.substack.com/p/your-coding-agent-has-a-fatal-flaw?r=bpg99)
- [Week 3 — Replay Is an Experiment, Not a Rerun](https://github.com/silsgah/coding-agent-course/tree/master/week-03-replay-model-swap)
- [Week 4 — Permission Is Not Containment](https://github.com/silsgah/coding-agent-course/tree/master/week-04-containment-sandboxing)
- [Week 5 — Context Is a Budget, Not a Memory Dump](https://github.com/silsgah/coding-agent-course/tree/master/week-05-context-budget)
- [Week 6 — The Harness Is the Product](https://github.com/silsgah/coding-agent-course/tree/master/week-06-harness-design)
- **Week 7 — Parallelism Is a Coordination Problem**
- Next: **Week 8 — An Evaluation Is Evidence, Not a Vibe**

## First decide whether the task deserves fan-out

Parallel agents do not make sequential reasoning parallel. If a task is “understand the architecture, change a central abstraction, update every caller, then run the tests,” each later step depends on the earlier one. Sending that work to several children creates incompatible assumptions and duplicated edits.

Fan-out is appropriate when the evidence-gathering branches are independent:

```text
Good fan-out                         Poor fan-out

map source modules                   design API → implement it → update callers
locate tests                         reproduce bug → identify cause → patch
inspect configuration                migrate schema → update consumers → deploy
find references                      understand failure → choose remediation
```

The parent agent is therefore not merely a dispatcher. It is responsible for choosing independent angles and for refusing a decomposition that is too broad or too vague to be useful.

In `decode`, the parent makes **one** `agent(prompts=[...])` tool call. The harness validates those prompts before it creates any children: the list cannot be empty, cannot exceed the fan-out cap, and each brief must contain enough substance to guide a real investigation. A prompt such as “look around” is not an exploration plan; it is an expensive way to obtain an ungrounded summary.

When the input fails the contract, the harness returns a model-retry message naming the problem. No child is spawned. This is a valuable pattern: spend a cheap parent correction turn before spending several child model calls on bad work.

## The child is the same loop, re-entered with less authority

The canonical design does not create a separate process, a durable child session, or a second agent framework for every subtask. A child is the same agent loop re-entered in-process with fresh, narrowed dependencies.

That keeps the mechanism small:

```text
parent agent
  │
  └── agent(prompts=[p1, p2, p3])
          │
          ├── Explore child 1: fresh history + read-only tools
          ├── Explore child 2: fresh history + read-only tools
          └── Explore child 3: fresh history + read-only tools
                    │
                    ▼
            labelled aggregate returned to parent
```

The boundaries are logical rather than process-isolated. Children share the parent process and model client, which keeps them cheap. They also share the parent’s fault domain. That trade-off is acceptable because this subagent is deliberately an **Explore** persona rather than a general coding worker.

Its tool surface is structurally restricted to read-only investigation: `read`, `glob`, `grep`, and LSP. It cannot edit files, run arbitrary shell commands, fetch the web, write task lists, ask the user a question, or recursively call the `agent` tool.

Those exclusions are design decisions, not omissions:

- A child that can edit or run `bash` creates parallel side effects that need a much stronger coordination and isolation model.
- A child that can ask the user can deadlock against the parent’s single decision channel.
- A child that can spawn children makes recursion and cost growth structurally easy.

Least privilege is especially important in a swarm. Four read-only researchers are manageable. Four workers with filesystem writes, shell access, and inherited credentials are a different product.

## Parallelism must be a harness guarantee

Models can emit several tool calls in one response, but a real product should not outsource its concurrency policy to whatever shape the model happens to choose. The `decode` harness gathers child runs itself and enforces a configurable semaphore for active child attempts.

The limit has two benefits:

1. It protects provider rate limits, local resources, and the user’s budget.
2. It makes concurrency observable and testable: children genuinely overlap, but the peak never exceeds the configured bound.

There is a second budget inside each child. Usage limits cap its request count, token use, and tool-call behavior independently of the parent. The parent’s context gauge deliberately does not absorb child usage; otherwise a few investigations could make the main conversation appear full even though their detailed transcripts never enter it.

This is not hiding cost. It is accounting for it at the correct level. The swarm has its own resource envelope, and each child has a finite share of it.

## The report contract protects the parent’s context

The most common multi-agent design error is to return every child transcript to the coordinator. That gives the parent all the context bloat Week 5 worked to avoid—multiplied by the fan-out width.

Instead, child transcripts are ephemeral. A child performs its scoped investigation, returns a final report, and its private model/tool history is discarded. The parent receives one labelled aggregate:

```text
## Subagent 1 — "Map the package boundaries"
<bounded report>

## Subagent 2 — "Locate the test entry points"
<bounded report>

## Subagent 3 — "Trace configuration loading"
<bounded report>

## Synthesis footer
<how the parent should use the evidence>
```

The aggregate is deterministic in prompt order, not completion order. That makes a transcript readable and makes a replay or test comparison stable even when child durations differ.

Most importantly, the fold has a **shared byte budget**. If the configured result budget is `B` and the parent requested `N` children, each report receives at most `B / N` bytes through the same truncation mechanism used elsewhere in the harness. The footer is harness overhead, not an excuse to steal from one child’s share.

This makes the parent-facing context cost roughly independent of width. More children can improve coverage, but they cannot silently flood the coordinator with an ever-growing transcript.

## A result is not useful merely because it is fluent

A child may return polished prose without investigating anything. The resilient fan-out layer treats the child report as untrusted output and validates a simple but meaningful property: it must be non-empty and supported by actual tool use.

If a child returns a report with zero tool calls, the harness retries that child once with an explicit nudge to inspect the workspace. If the retry is still unusable, the child is not retried forever and its failure becomes an honest note in the parent aggregate.

```text
child report valid? ── yes ──► truncate and fold
         │
         no
         │
   first failure? ── yes ──► retry once with a nudge
         │
         no
         ▼
  fold a visible "no usable report" note
```

The important detail is that siblings survive. A failed inspection of one package must not discard useful reports from the others. And a failure note is better product behavior than a fabricated conclusion: the parent model and the human operator can see which angle needs follow-up.

## Silence by default is a coordination decision too

If three children each emit every `glob`, `read`, and `grep` event into the parent terminal, the interactive experience becomes unreadable. The default behavior is therefore silent-until-done: children return their aggregate result without flooding the parent event sink.

The system can expose verbose child activity when an operator explicitly asks for it, rendered as clearly indented child events. The default remains quiet because the parent’s task is to synthesize evidence, not to turn the terminal into an interleaved log stream.

This is a small UX choice with a large systems implication. Observability should be available without making normal operation noisy or leaking implementation detail into the parent’s working context.

## What gets persisted, and why

The parent session records the spawn call and the bounded aggregate. It does **not** persist every child’s private transcript. That preserves the parent’s durable story—what was requested and what evidence returned—without making resume and replay carry a swarm’s worth of internal tool chatter.

Because Explore children are read-only and their reports are deterministic at the parent boundary, the single fan-out tool result remains replay-safe. The external runtime does not need to understand every internal child event to preserve the parent’s execution contract.

This is a useful general rule for orchestration: choose the smallest durable boundary that preserves the semantics the next layer actually needs.

## Test the failure matrix, not only the speedup

“It ran four agents at once” is not a sufficient test. The canonical subagent capstone exercises the real agent loop, tool registration, prompt guards, semaphore, scoped child dependencies, aggregate fold, session persistence, and resume path together. Its checks include:

- children overlap in time but never exceed the configured concurrency cap;
- read-only children use their allowed tools without asking the human permission resolver;
- a child cannot recursively spawn another child;
- every child receives its fair share of the aggregate byte budget;
- child usage does not corrupt the parent context gauge;
- an unsupported, zero-tool-call report retries exactly once and then becomes a visible failure note;
- healthy siblings still complete when one child fails; and
- parent persistence includes the request and aggregate, never private child transcripts.

The test suite includes a live provider smoke test behind an explicit credential gate, but the core capstone is hermetic: it uses a scripted model to prove orchestration semantics without treating a provider response as a deterministic test fixture.

## The larger lesson

Parallelism does not come from adding an `asyncio.gather()` call to an agent. It comes from defining contracts at every boundary:

```text
independent prompts
  + restricted authority
  + bounded concurrency and usage
  + validated, budgeted reports
  + honest failure handling
  = useful parallel exploration
```

Once those controls exist, a parent agent can explore a repository faster without losing its own context, authority model, or audit trail. Without them, a swarm is merely a faster way to produce confusion and cost.

Next, I will move from “the system ran” to the harder question: how do we establish evidence that a harness change actually makes the coding agent better?

---

*This is Week 7 of my “Building a Coding Agent From Scratch” series. See the [canonical subagents lesson](https://github.com/silsgah/building-a-coding-agent-from-scratch-course/tree/master/lessons/06-subagents) and the [companion Week 7 lab](https://github.com/silsgah/coding-agent-course/tree/master/week-07-parallel-subagents).*
