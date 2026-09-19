# Building a Coding Agent From Scratch, Week 7: Parallelism Is a Coordination Problem

### A swarm is not “more agents.” It is a contract for splitting work, limiting authority, and returning evidence that a coordinator can trust.

Up to this point in the series, I have been making one coding agent more reliable: first giving it tools, then making it resumable, replayable, contained, context-aware, and easier to inspect as a Python object.

This week changes the shape of the problem. Some tasks are not hard because they require deep sequential reasoning; they are slow because they contain several independent investigations. A repository review might require reading the README, locating tests, mapping dependencies, and examining the source layout. One agent can do those things in sequence. It does not have to.

The obvious answer is to run several agents at once. The dangerous answer is to run several agents at once without deciding what they are allowed to do, how much they may spend, what counts as a result, or what happens when one of them fails.

Week 7 is about that difference: parallel subagents as a bounded execution system, not a collection of unconstrained chats.

This is the seventh installment in my *Building a Coding Agent From Scratch* series:

1. **Week 1:** the tool-using agent loop.
2. **Week 2:** durable checkpoints and resumability.
3. **Week 3:** replaying recorded state to compare decisions.
4. **Week 4:** permissions and sandboxing.
5. **Week 5:** context as a finite budget.
6. **Week 6:** an inspectable agent-as-object harness.
7. **Week 7:** bounded parallel subagents.

The Week 7 implementation is available in the [course repository](https://github.com/silsgah/coding-agent-course/tree/master/week-07-parallel-subagents).

## When parallelism is actually useful

Parallelism helps only when the work is independent.

“Read these four unrelated modules and report what each does” is a good fan-out problem. Each child can work from a fresh context and return a compact report. “Understand the architecture, change a core abstraction, then update every caller” is not. Those later steps depend on the earlier ones, so parallel work increases the chance of contradictory assumptions and duplicated effort.

That gives the coordinator its first responsibility: reject a vague task decomposition and produce only independent work items. In this lesson, the model is asked to return a JSON array of at most five read-only subtasks. The response is then treated as untrusted input: parsed, deduplicated, trimmed, and capped before it can create agents.

```python
def parse_subtasks(text: str, maximum: int = 5) -> list[str]:
    candidate = json.loads(text)
    if not isinstance(candidate, list):
        raise ValueError("Task decomposition must be a JSON array")

    subtasks = []
    for item in candidate:
        task = str(item).strip()
        if task and task not in subtasks:
            subtasks.append(task[:500])

    if not subtasks:
        raise ValueError("Task decomposition produced no usable subtasks")
    return subtasks[:maximum]
```

The cap is not an arbitrary UI choice. Without it, one malformed or overenthusiastic decomposition can produce dozens of model calls, explode cost, saturate rate limits, and make the final synthesis less useful. Fan-out must be budgeted before it is fast.

## The child contract is the real API

A child agent does not return its entire conversation history. That would recreate the context problem from Week 5 at the coordinator layer. Instead, each child returns one validated report:

```python
@dataclass(frozen=True)
class SubagentReport:
    subtask: str
    status: str             # success | partial | failed
    summary: str
    key_facts: tuple[str, ...]
    tokens_used: int
    tool_calls: int
    elapsed_seconds: float
    error: str | None = None
    attempt: int = 1
```

This small object does several jobs at once.

It gives the coordinator a stable interface regardless of which model ran the child. It limits report summaries and fact lists so one verbose child cannot consume the merger’s entire context. It retains operational evidence—token use, tool calls, elapsed time, retries—so the parent can distinguish a useful answer from a merely fluent one. And it leaves failures visible instead of converting them into a convincing but unsupported final answer.

Each child also receives a separate budget:

```python
@dataclass(frozen=True)
class ChildBudget:
    max_tokens: int = 8_000
    max_iterations: int = 6
    timeout_seconds: float = 60.0
```

Budgets are a core part of the contract, not just observability. They prevent a child from consuming the swarm’s resources indefinitely because it is stuck in a tool loop or waiting on a provider. A production system should add an aggregate swarm-level budget as well; this lesson keeps that concern explicit rather than hiding it behind an unlimited `asyncio.gather()`.

## Bounded fan-out, not unlimited concurrency

The scheduling core is deliberately straightforward. A semaphore limits the number of active children, and `asyncio.wait_for` bounds each child’s wall-clock time:

```python
async def bounded_child(subtask, agent_id, semaphore, budget, provider_factory, tool_executor):
    async with semaphore:
        try:
            return await asyncio.wait_for(
                run_child_agent(subtask, agent_id, budget, provider_factory, tool_executor),
                timeout=budget.timeout_seconds,
            )
        except TimeoutError:
            return SubagentReport.failed(
                subtask,
                f"Timed out after {budget.timeout_seconds:.0f}s",
                budget.timeout_seconds,
            )
```

This creates an important separation. The coordinator controls *how many* children are in flight. The child budget controls *how long* a specific child may continue. The report contract controls *what* comes back. No individual model response gets to decide all three.

The swarm retries only `failed` children once, with a larger token budget. It does not retry every partial answer automatically. A partial result may be a legitimate signal that the child reached a cost or iteration limit; blindly retrying it can turn a limit into a loop. The coordinator preserves that evidence for the final answer.

## Parallelism multiplies authority too

The first implementation of this lesson inherited the broad tool surface from the earliest agent loop. That was convenient for a demo, but it is the wrong default for a swarm. Four parallel agents with shell and write access are not just four times faster; they are four simultaneous sources of side effects.

The current default is intentionally narrower. Exploration children can only use two workspace-contained, read-only tools:

- `read_file`
- `list_files`

They cannot write files, invoke a shell, or make network requests. Path resolution rejects `..` and symlink escapes beyond the workspace. Broader capabilities must be injected deliberately—and, in a real deployment, routed through the Week 4 sandbox with per-child credentials, filesystem scope, network policy, and approval rules.

This is the same principle that guided the earlier permission and sandbox work: start with the smallest authority that completes the task. Fan-out makes least privilege more important, not less.

## Swarm versus single agent: measure the right thing

For independent tasks, parallel execution reduces wall-clock time because the slowest child, not the sum of child durations, dominates the work. The lesson includes a deterministic comparison using the same simulated worker in both modes:

```text
single agent (sequential): 0.124s | 400 tokens | 4 successful children
swarm (parallel):          0.032s | 400 tokens | 4 successful children
```

The point of this example is deliberately narrow. It demonstrates scheduling: the same independent work completes faster in parallel, without claiming that a swarm is inherently more intelligent or more token-efficient.

In live model work, the comparison has more dimensions. A swarm adds coordinator prompts, report-merging cost, and potential duplication across children. A single agent keeps one coherent context and may outperform the swarm when the work is tightly coupled. The correct question is not “should I always use multiple agents?” It is “does this task have independent evidence-gathering branches whose results can be merged safely?”

## What I tested

The Week 7 module now has six deterministic tests that run without an API key. They verify:

- invalid child budgets and reports are rejected;
- decompositions are parsed, deduplicated, and capped;
- default exploration tools refuse writes and workspace escapes;
- a child follows the complete model → tool → result → report cycle;
- a failed child retries exactly once; and
- parallel scheduling completes independent work faster than the same sequential schedule.

The implementation also separates provider construction and tool execution from the child loop. Tests inject scripted providers and safe executors rather than relying on live network calls. That makes the orchestration contract testable independently of model behavior.

## The larger lesson

The most useful way to think about a subagent is not as another autonomous worker. It is as a bounded function call with a model in the middle:

```text
subtask + scoped tools + budget → validated report
```

Once that boundary is explicit, the coordinator can schedule work, account for cost, surface failures, and merge evidence without carrying every child’s private transcript. Parallelism becomes a systems-design decision rather than a prompt trick.

Next, the course moves to evaluation: defining tasks, thresholds, and regression tests that can tell us whether these harness changes actually improve a coding agent rather than simply making it more elaborate.

---

*This is Week 7 of my “Building a Coding Agent From Scratch” series. The project now supports bounded, read-only exploration subagents with validated reports, concurrency limits, timeouts, and controlled retry behavior.*
