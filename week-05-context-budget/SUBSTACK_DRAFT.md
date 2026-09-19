# Building a Coding Agent From Scratch, Week 5: Context Is a Budget, Not a Memory Dump

### The agent does not become more capable because it sees more text. It becomes more capable when the text it sees is relevant, current, and small enough to reason over.

By Week 4 of this series, the coding agent could act, recover from interruption, replay a decision from a recorded checkpoint, and run tools with clearer safety boundaries. That is a useful harness—but it still has a failure mode that appears only when tasks get long.

Every tool result, file excerpt, instruction, user follow-up, and assistant response competes for the same finite context window. On a short task, this is invisible. On a long task, old command output crowds out the facts the model needs now. The agent starts to repeat exploration, loses constraints, or reasons from stale information.

This week is about treating context as a budget.

The goal is not to find a larger context window and fill it. The goal is to decide what deserves to occupy the window at each step, reserve room for the next response, and remove or summarize information only when that trade-off is justified.

This is Week 5 of my *Building a Coding Agent From Scratch* series:

1. **Week 1:** build the tool-using agent loop.
2. **Week 2:** make the loop resumable with durable checkpoints.
3. **Week 3:** replay recorded state to compare decisions and models.
4. **Week 4:** contain tool execution with permissions and sandboxing.
5. **Week 5:** manage the information the model receives while it works.

The Week 5 code is available in the [course repository](https://github.com/silsgah/coding-agent-course/tree/master/week-05-context-budget).

## Why context needs an explicit budget

A context limit is not just a provider constraint. It is an engineering constraint on every harness component.

The system prompt consumes tokens. Tool schemas consume tokens. Project instructions, saved memory, and loaded skills consume tokens. Most importantly, the conversation grows whenever an agent reads a file or runs a command. If a command returns 10,000 characters, that output is now part of the next model request unless the harness intervenes.

The useful mental model is a balance sheet:

```text
context window
├── system instructions and tool definitions
├── project instructions and durable memory
├── skills loaded for this task
├── conversation and tool results
└── reserved capacity for the next model response
```

The final line is easy to miss. Sending a prompt that almost fills the window does not leave enough room for a model to call a tool or write an answer. The harness should compact before the hard limit, not after it.

In this implementation, `ContextBudget` tracks these categories separately and fires compaction at a configurable threshold—80% by default—while reserving 4,000 tokens for the next response:

```python
@dataclass
class ContextBudget:
    max_tokens: int = 128_000
    compaction_threshold: float = 0.8
    reserved_for_response: int = 4_000

    system_tokens: int = 0
    memory_tokens: int = 0
    history_tokens: int = 0

    @property
    def needs_compaction(self) -> bool:
        return self.used_tokens / self.max_tokens >= self.compaction_threshold
```

The token calculation is deliberately approximate—roughly four characters per token—because the lesson is about the control loop, not a tokenizer implementation. A production harness should use the tokenizer associated with its model and include provider-specific framing overhead. Even an estimate is valuable, though: it turns a hidden source of degradation into an observable signal.

## Compaction is a lossy but necessary handoff

When the threshold is crossed, the agent keeps recent messages intact and asks a model to summarize the earlier part of the conversation. The summary must preserve decisions, facts, file paths, and unfinished work, because it becomes the next agent’s working memory.

```python
old_messages = messages[1:-keep_recent]
recent_messages = messages[-keep_recent:]

response = await provider.chat([
    Message(role="system", content=(
        "Summarize the conversation concisely, preserving key facts, "
        "decisions, and file paths."
    )),
    Message(role="user", content=old_text),
])

return [
    messages[0],
    Message(role="assistant", content=f"[Previous conversation summary]\n{response.content}"),
    *recent_messages,
]
```

There is no magic here. Compaction trades detail for capacity. A weak summary can erase the reason a decision was made; an overly long summary fails to reclaim enough room. That is why the harness preserves the newest messages verbatim and why compaction should be measured, tested, and triggered only when necessary.

It also explains why tool output discipline matters. A better first move than summarizing a 50,000-character file is not to put all 50,000 characters into context. File reads and command output need limits; symbol lookup or targeted search is often a better source of evidence than a whole-file dump.

## Three kinds of memory, three different jobs

Week 5 separates durable knowledge from the live conversation rather than treating all prior text as one blob.

**AGENTS.md** is project-owned instruction. It tells an agent how to work in a particular repository: conventions, architecture, commands to run, and areas that must not be changed. It should load at session start because it is part of the project contract.

**MEMORY.md** is agent-learned knowledge. It can preserve stable discoveries across sessions: an unusual test command, an important package boundary, or a mistake that should not be repeated. It belongs in a clearly scoped location such as `.agent/MEMORY.md`, not in an invisible provider-side store.

**Skills** are curated, task-specific knowledge loaded on demand. A Python skill, a database migration skill, or a release skill should not consume tokens on every task. The harness discovers available skills and injects the chosen one only when it is relevant.

This separation makes context auditable. A developer can inspect exactly which project instructions, learned notes, and skill text were sent to a model. It also forces a useful question for every addition: does this information help the next decision enough to justify its token cost?

The memory demo is safe to run locally. It uses a disposable directory unless a project path is explicitly supplied, so a course example will not quietly create `.agent/MEMORY.md` or skills inside the repository you happen to be standing in.

## Focused context beats whole files

An LSP can answer questions such as “where is this symbol defined?” or “what references this method?” without handing the model an entire source file. That is a powerful context-saving primitive: send the function or class that matters, not every unrelated line around it.

The lesson includes a dependency-free Python symbol example as a stand-in for a full language-server integration:

```bash
python code/lsp_context.py code/context_budget.py ContextBudget
```

It parses the source with Python’s AST and returns only the requested top-level class or function. A production harness would call a language server for definitions, references, type information, and cross-file navigation. The principle is the same: retrieval should narrow context before the model sees it.

## The NOOA lesson: prevent growth before you compact it

The NOOA approach offers a useful counterpoint. Instead of carrying one ever-growing conversation across a complex task, it treats method boundaries as natural context boundaries. A completed method can return a structured result or concise handoff; the next method begins with the state it needs, rather than every observation that produced it.

This is not an argument that compaction is unnecessary. Long, interactive agent turns still need a strategy for their history. It is an argument that architecture can prevent a large part of the problem. A pipeline of focused methods has smaller prompts, clearer inputs and outputs, and fewer opportunities for irrelevant detail to accumulate.

The new offline comparison tool makes that trade-off visible without requiring an API key:

```bash
python code/nooa_comparison.py
```

It estimates the prompt volume and peak context of two strategies for representative subtasks:

- a growing conversation that may need compaction; and
- fresh, method-boundary contexts for each focused subtask.

It is not a benchmark and does not judge answer quality. A method boundary can lose essential shared context if the handoff is poor. The tool is intentionally honest about that limitation: it illustrates the context-cost mechanism, while live evaluation must determine whether a given decomposition still completes the task correctly.

## What I tested

The Week 5 additions include five offline tests covering budget accounting, summary compaction, scoped project memory and skills, focused symbol extraction, and the context-cost comparison. The examples that do not need a model—memory, focused-symbol retrieval, and strategy comparison—run without credentials. The interactive budget loop remains model-backed by design.

That split matters. Harness logic should be testable without making a live model call, while the behavior of a particular model belongs in a separate integration or evaluation run.

## The series is moving from capability to control

The first weeks made the agent able to act, survive, replay, and operate more safely. Context engineering is a different kind of control: it governs what the agent is allowed to know at the moment it makes a decision.

The strongest agent is not the one with the longest transcript. It is the one with the smallest useful set of instructions, evidence, and memory for the step in front of it.

That is the discipline Week 5 adds: budget every token, preserve durable knowledge deliberately, retrieve the smallest relevant context, and make compaction a measured handoff rather than a last-minute rescue.

---

*This is Week 5 of my “Building a Coding Agent From Scratch” series. The project now has a context budget manager, project and learned memory, on-demand skills, focused symbol context, and an offline method-boundary comparison.*
