# Building a Coding Agent From Scratch, Week 5: Context Is a Budget, Not a Memory Dump

### A coding agent does not become more capable because it sees more text. It becomes more capable when it has the right evidence, in the right form, with room left to reason.

The first four weeks of this series built a coding agent that can act, survive interruption, replay a recorded decision, and operate inside clearer authority boundaries. Those are necessary foundations. They also expose the next systems problem: a long-running agent is constantly manufacturing context.

Every file it reads, command it runs, tool schema it receives, instruction it loads, and decision it records competes for the same finite model input window. On a small task this is invisible. On a real repository it eventually becomes the failure mode: useful recent evidence is crowded out by old terminal output, stale explorations, and entire files that never needed to be in the prompt.

This week is about treating that window as a budget.

The point is not to find a larger model and fill it. The point is to measure the available capacity, preserve the information the next decision actually needs, and reduce or retrieve everything else deliberately.

This installment follows the canonical [`decode`](https://github.com/silsgah/building-a-coding-agent-from-scratch-course) implementation and its [Context Engineering lesson](https://github.com/silsgah/building-a-coding-agent-from-scratch-course/tree/master/lessons/04-context-engineering). The companion lab remains a small teaching aid; the runtime is where the budget, compaction, memory, skills, and retrieval behavior are integrated and tested together.

## Series navigation

- [Week 1 — Why the Agent Loop is 20 Lines of Code](https://kwablagah.substack.com/p/why-the-agent-loop-is-20-lines-of?r=bpg99)
- [Week 2 — Your Coding Agent Has a Fatal Flaw](https://kwablagah.substack.com/p/your-coding-agent-has-a-fatal-flaw?r=bpg99)
- [Week 3 — Replay Is an Experiment, Not a Rerun](https://github.com/silsgah/coding-agent-course/tree/master/week-03-replay-model-swap)
- [Week 4 — Permission Is Not Containment](https://github.com/silsgah/coding-agent-course/tree/master/week-04-containment-sandboxing)
- **Week 5 — Context Is a Budget, Not a Memory Dump**
- Next: **Week 6 — The Harness Is the Product**

## The context window is working memory

Think of the context window as a workbench, not an archive. It has to hold enough of the current task to support the next action, but every extra object on the bench makes the relevant ones harder to find.

For a coding agent, the budget has many claimants:

```text
model input window
├── system prompt and tool definitions
├── repository instructions and durable memory
├── task-specific skill guidance
├── conversation history
├── file excerpts and tool results
└── reserved room for the next model response and tool call
```

The last item is crucial. A harness that sends an input prompt right up to the model limit has not made maximum use of the window; it has left too little room for the model to answer or call a tool. This is why the `decode` runtime uses a configurable context-window value and reserve fractions, rather than a vague “compact when it feels large” heuristic.

Measurement must also be honest. Character-count estimates are fine for an introductory demonstration, but the canonical runtime uses the provider-reported input-token usage for its trigger. The configured window is intentionally explicit: providers do not expose one universal, reliable context-window field through the agent library. An operator sets the window appropriate to the active model, and the runtime compares observed input usage to it.

Context engineering without measurement is folklore.

## Two automatic interventions, not one last-minute summary

Compaction is often described as “summarize the conversation when it gets too long.” That hides an important design choice. Not every threshold crossing deserves an expensive, lossy model summary.

`decode` uses a cheapest-first cascade:

| Pressure level | Intervention | What changes |
| --- | --- | --- |
| Near 60% of the configured window | **Microcompaction** | Older tool-result bodies are replaced in memory by an explicit elision marker. |
| Near 80% of the configured window | **Full compaction** | A model summarizes older history; the summary plus a recent verbatim tail becomes the new context. |
| User requests `/compact` | **Full compaction** | The operator can force a deliberate handoff while the agent is idle. |

The percentages are reserves, not mystical constants. By default, microcompaction keeps a larger reserve and therefore fires first; full compaction keeps a smaller reserve and fires later. The invariant is simple: the cheap intervention must happen before the lossy one.

### Microcompaction: preserve structure, drop old bulk

Old tool output is often the largest part of a coding conversation and the least valuable part after it has served its purpose. Microcompaction replaces old tool-result content with a marker such as:

```text
[tool output elided by microcompaction]
```

It does not remove messages or split a tool-call/result pair. It is idempotent. And, critically, it is **in-memory only**. The session’s append-only log retains full fidelity, so a resumed session can rebuild the original history and apply the same temporary reduction again if required.

That is a thoughtful trade-off: keep recovery evidence intact while preventing stale output from monopolizing the next prompt.

### Full compaction: a deliberate, persistent handoff

At higher pressure, eliding output is not enough. Full compaction asks a model to turn older history into a structured working record. The result is not an arbitrary paragraph. It follows a fixed skeleton:

```text
# Conversation summary
## Goal
## Constraints & Preferences
## Progress
### Done
### In Progress
### Blocked
## Key Decisions
## Next Steps
## Critical Context
```

The post-compaction history is intentionally small and explicit:

```text
[summary of earlier work] + [recent verbatim tail]
```

The retained tail is cut at a safe conversation boundary so the harness never leaves the model with one half of a tool interaction. The previous summary becomes part of later compactions, so successive handoffs compose rather than discarding earlier decisions one summary at a time.

Unlike microcompaction, full compaction is written to the append-only session log as a typed checkpoint. On resume, the runtime uses the compacted state—summary and tail—rather than replaying the entire pre-compaction transcript. The durable record, in-memory history, and persistence cursor must move together. If they do not, a resumed agent and a live agent would reason from different histories.

This is the difference between a clever prompt trick and a runtime feature.

## A summary is lossy, so prevent avoidable growth first

Compaction is a necessary handoff, not an excuse to dump unlimited text into the model context. The better first question is: should this information have entered the prompt in this form at all?

The runtime uses several complementary moves:

- **Truncation:** bound large tool outputs before they dominate a turn.
- **LSP retrieval:** ask for a definition, references, types, or diagnostics instead of pasting a whole codebase or file.
- **Skills:** advertise available playbooks cheaply and load their full content only when one is invoked.
- **Memory:** preserve stable, useful knowledge across sessions in an inspectable project file rather than retaining every transcript detail forever.

These moves solve different problems. Truncation limits accidental bulk. LSP improves the precision of code retrieval. Skills keep specialized procedures dormant until relevant. Memory carries durable facts forward. Compaction repairs an already long conversation.

Treating them as one feature would make the harness impossible to tune and impossible to test.

## Memory has a different job from conversation history

The phrase “agent memory” can obscure more than it explains. There are at least three distinct artifacts in this system:

| Artifact | Owner | Purpose |
| --- | --- | --- |
| Repository instructions such as `AGENTS.md` | Project | Constraints, conventions, commands, and architecture rules. |
| `.decode/MEMORY.md` | Agent plus operator | Stable facts learned over multiple sessions. |
| Session log | Runtime | High-fidelity, chronological execution record for resume and audit. |

They should not be merged into a single opaque store.

Repository instructions are part of the task contract. Durable memory should contain compact discoveries that remain useful, such as a non-obvious test command or an important package boundary. The session log is evidence, not a prompt to inject in full on the next task.

At the end of a session, `decode` uses a separate memory write-back step to update its durable memory. When that file grows too large, it too is compressed deliberately rather than silently dropping the oldest lines. This gives the next session a concise orientation without pretending that the whole prior conversation is permanently relevant.

## Skills are configuration before they are context

Skills are a particularly good example of an idea that sounds expensive until it is implemented carefully. A repository may have dozens of specialized playbooks: release procedures, migration conventions, debugging workflows, or interface-specific constraints. Loading every one on every turn would be wasteful and distracting.

Instead, the harness can place an index of available skill names in context and load the full Markdown playbook only when the agent calls for it. A long terminal-arcade skill may be hundreds of lines, but it costs almost nothing until it is actually useful to the task.

This is not merely token optimization. It makes the agent’s context auditable: an operator can see which skill was selected, why it was loaded, and exactly what guidance it supplied.

## LSP is a context move, not just editor tooling

Language-server integration is often filed under developer experience. In an agent harness, it is a context-engineering primitive.

Suppose the agent needs to understand a function. A naïve strategy reads the complete source file, then reads callers, then searches the project. A better strategy asks the language server for the definition, references, type information, and diagnostics. The model receives the small, high-signal slice it needs to make the next decision.

The lesson’s headless demonstration makes this concrete: memory injection lets the agent begin with the project conventions already available, while an LSP query retrieves definitions and references instead of turning file dumping into a retrieval strategy.

Focused retrieval does not eliminate judgment. The model may still need to inspect surrounding code. It changes the default from “send everything just in case” to “retrieve the smallest evidence that answers the current question.”

## The interactive controls matter

Long-running tools need to make invisible pressure observable. The interactive `decode` experience exposes a context gauge in its footer, so the operator can see the window filling rather than discovering the problem through a provider error.

It also exposes `/compact` as an idle-only command. This is a small but important interface decision. A human can request a clean handoff before beginning a new phase of work, but cannot mutate the agent’s history midway through an active turn. The runtime owns the single-flight state transition; the user owns the decision to trigger it when the agent is idle.

Good agent UX does not hide resource management. It gives the operator a legible model of what the system is doing.

## What must be tested

This design makes specific, testable promises. The canonical project verifies them through unit tests, an integration capstone, and a regression probe for compaction survival. The important checks are not “did a summary appear?” They include:

- microcompaction fires before full compaction at the configured reserves;
- microcompaction preserves message structure, elides only older tool bodies, and never writes a compaction record;
- full compaction yields exactly a structured summary plus a safe recent tail;
- the append-only log resumes into the compacted state without duplicating old messages;
- a failed summarizer is visible as a failed compaction outcome rather than silent corruption; and
- a fact needed after compaction remains available to the agent in a regression evaluation.

That final point matters most. A compacted conversation that is cheaper but forgets a critical constraint is not a success. Resource savings are measurements; task continuity is the outcome.

## The larger lesson

Week 5 moves the series from managing what an agent may *do* to managing what it may *know at once*.

The strongest coding agent is not the one with the longest transcript or the biggest advertised window. It is the one that measures pressure, keeps current evidence close, retrieves code precisely, records durable knowledge separately, and performs a structured handoff before the context becomes unusable.

Context is not an infinite memory. It is a working budget. Treat it that way and an agent can stay coherent long after the first impressive demo would have drowned in its own output.

Next, I will look at the harness itself: the less visible software around the model loop that determines whether an agent is debuggable, testable, and safe to evolve.

---

*This is Week 5 of my “Building a Coding Agent From Scratch” series. Explore the [canonical context-engineering lesson](https://github.com/silsgah/building-a-coding-agent-from-scratch-course/tree/master/lessons/04-context-engineering) and the [companion Week 5 lab](https://github.com/silsgah/coding-agent-course/tree/master/week-05-context-budget).*
