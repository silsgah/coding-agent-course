# Building a Coding Agent From Scratch, Week 3: Turning Checkpoints into Experiments

In the first two weeks of this series, I built the smallest useful coding agent and then made its execution durable.

Week 1 established the core loop: give a model a task, let it choose a tool, run that tool behind a permission gate, feed the result back, and repeat until it can answer. The loop is short. The engineering around it is not.

Week 2 addressed the first serious operational problem: a process can stop halfway through a task. Rather than rerunning completed work, the agent writes an append-only record of user messages, tool calls, tool results, and completed steps. On restart, it rebuilds the conversation from that record and continues.

This week changes the purpose of that record. A checkpoint is not only a recovery mechanism. It is also a controlled starting point for an experiment.

The Week 3 deliverable is a replay harness: choose a completed point in a run, preserve everything before it, and ask the same or a different model to continue from there. It turns the question “why did the agent make that choice?” into something testable.

## From recovery log to experimental boundary

When an agent produces a poor result, reading the transcript is necessary but often insufficient. The important question is usually local: at which decision did the run begin to diverge from a better path?

Starting a new run from the original prompt does not isolate that decision. The model can take different actions much earlier, tools can return different results, and the comparison quickly stops being meaningful. A replay needs to retain the exact context that led to the point under investigation.

The harness therefore treats each completed tool call as a potential fork boundary. A replay at step *N* contains:

- the original user request;
- every model tool call and tool result through completed step *N*;
- replay metadata identifying the source session, fork step, and selected model; and
- only the new events produced after the branch begins.

The source checkpoint is never altered. The replay branch gets its own append-only JSONL file, so it can be inspected, compared, and replayed again in turn.

That distinction matters. This is not a prompt comparison. It is a counterfactual experiment over a fixed agent state: given the same task, conversation history, tool outputs, and available tools, what happens next if we change the model?

## What I built

The implementation has three small pieces.

`replay_harness.py` creates a fresh session or forks an existing one. It reconstructs the provider-neutral message history from the checkpoint, continues the normal agent loop, and writes a `run_metrics.json` summary beside the event log.

`model_swap.py` creates one branch per requested model from the same source session and fork point. Each branch receives the same inherited prefix; model choice is the intentionally changed variable.

`comparison_report.py` reads any set of sessions and generates a Markdown report with tool-call count, prompt and completion tokens, elapsed time, estimated token cost where pricing is known, errors, and the final answers for side-by-side review.

The usage looks like this:

```bash
# 1. Create an observed run.
python code/replay_harness.py \
  --task "List the files here and create a summary.md"

# 2. Branch the same checkpoint with two models.
python code/model_swap.py \
  --original sessions/latest \
  --from-step 1 \
  --models gemini-2.0-flash gpt-4o-mini

# 3. Produce a human-readable comparison.
python code/comparison_report.py \
  --runs sessions/swap-gemini-2-0-flash sessions/swap-gpt-4o-mini \
  --output comparison_report.md
```

`--from-step 0` starts immediately after the user request. A larger number starts after that many completed tool calls. The harness rejects an unavailable step rather than silently replaying a different state—a small guardrail that matters when a debugging tool is supposed to be trustworthy.

## Why the event log is the right unit of replay

The model itself does not carry durable state between API calls. Its effective state is the conversation and tool context sent with the next request. That is why Week 2 persisted events rather than trying to persist a model session, and it is why Week 3 can reconstruct a faithful branch without depending on a particular provider.

An append-only event log is also easier to reason about than a periodically overwritten snapshot. It makes the execution sequence visible: what the model requested, what the system actually executed, what the tool returned, and when the step became durable. At a fork, the inherited prefix is explicit rather than implied.

This design does not make replay perfectly deterministic. Models can be stochastic, external tools can change, and a replay that executes a write or shell command has real side effects unless it is run in a sandbox. Those are not edge cases; they are the next constraints the harness must address. For this week, the goal is narrower: make replay state explicit, isolate model choice, and make divergence observable.

## What the comparison can—and cannot—tell us

The generated report records objective operational signals:

- How many tools did the branch call?
- How many input and output tokens did it consume?
- How long did it take?
- What is the approximate model cost?
- What answer did it produce?

These measures are useful, but they are not a quality score. Fewer tool calls may mean better planning, or it may mean the model skipped necessary investigation. A cheaper answer may still be wrong. The report makes the trade-offs visible; it does not pretend to resolve them automatically.

That is an important boundary for an agent harness. Instrumentation should preserve evidence first. Evaluation rules—tests, task-specific assertions, or a calibrated judge—can then be layered on top. Week 8 of this series will make that evaluation loop explicit. This week supplies some of the data it will need.

## Testing the harness before trusting it

The replay code includes six offline tests. They cover checkpoint parsing, valid and invalid fork boundaries, history reconstruction, report generation, cost calculation, and a simulated replay branch. The simulated branch verifies the essential invariant: the original prefix is copied into a separate session, the new branch adds replay metadata and its own answer, and the recorded token metrics are persisted.

Those tests do not claim that a live model will produce a good answer. They verify the more fundamental behavior: that the harness preserves the state required to run the experiment without mutating the evidence it is based on.

## The progression so far

The series is deliberately building the harness before adding sophistication to the model layer.

Week 1 gave the agent the ability to act. Week 2 made those actions recoverable. Week 3 makes a completed or failed run inspectable as a branchable experiment.

That progression has changed how I think about coding agents. The useful unit is not a single model response; it is an execution system with a history, boundaries, and evidence. Once an agent can replay a decision from a known state, debugging becomes less like reading tea leaves and more like engineering.

Next, the project moves from observation to containment: running the agent’s tools inside a sandbox so that experimentation—and eventually greater autonomy—does not mean giving an LLM unrestricted access to the host machine.

---

*This is Week 3 of my “Building a Coding Agent From Scratch” series. Week 1 covered the bare agent loop; Week 2 added resumability and durable checkpoints; this installment adds replay and model-swap experiments.*
