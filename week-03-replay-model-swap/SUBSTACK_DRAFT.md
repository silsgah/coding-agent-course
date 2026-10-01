# Building a Coding Agent From Scratch, Week 3: Replay Is an Experiment, Not a Rerun

### A durable coding agent turns one observed run into evidence. A useful model comparison starts from that evidence, not from a fresh prompt.

In [Week 1](https://kwablagah.substack.com/p/why-the-agent-loop-is-20-lines-of?r=bpg99), I reduced a coding agent to its essential loop: ask a model what to do, execute a tool call, return the observation, and repeat. In [Week 2](https://kwablagah.substack.com/p/your-coding-agent-has-a-fatal-flaw?r=bpg99), I dealt with the first operational flaw in that loop: a process that loses its working state cannot reliably recover after an interruption.

This week changes why durability matters.

The useful outcome is not merely “the agent resumes.” A durable run is a record of what the agent saw and did. That record lets us ask a disciplined question:

> Given this exact request and this exact observed state, what would change if the next model call used a different model?

That is replay. It is not “run the prompt again and hope the second result is better.” It is a controlled fork of a recorded execution.

For this installment I am grounding the series in the canonical implementation, [`decode`](https://github.com/silsgah/building-a-coding-agent-from-scratch-course), specifically its [Durable Runtime lesson](https://github.com/silsgah/building-a-coding-agent-from-scratch-course/tree/master/lessons/03-durable-runtime). The small companion lab still explains the mechanics, but the runtime is where those mechanics become an operator-facing system.

## Series navigation

- [Week 1 — Why the Agent Loop is 20 Lines of Code](https://kwablagah.substack.com/p/why-the-agent-loop-is-20-lines-of?r=bpg99)
- [Week 2 — Your Coding Agent Has a Fatal Flaw](https://kwablagah.substack.com/p/your-coding-agent-has-a-fatal-flaw?r=bpg99)
- **Week 3 — Replay Is an Experiment, Not a Rerun**
- Next: **Week 4 — Permission Is Not Containment**

## Why a second run is not a comparison

Suppose an agent receives a repository task. It lists files, reads configuration, runs a command, and then chooses a poor next action. The intuitive response is to send the original prompt to another model.

But that changes almost everything at once. The second model may inspect a different file first. A live command can return different output. A different early plan changes the context of every later decision. If the result improves, we cannot honestly attribute that improvement to the model swap.

Replay defines the boundary instead:

```text
Observed execution                     Replay fork

user request                           user request            inherited
model request                          model request           inherited
tool call + observation                tool call + observation inherited
checkpoint: model request              checkpoint anchor
next model decision                    replacement model call  new
downstream tool calls                  downstream tool calls   new
```

The fork inherits the evidence before the selected checkpoint. It does not inherit the decision after it. That makes divergence meaningful: both branches arrived at the fork with the same recorded context; their later behavior is the experiment.

## An interactive agent is not automatically a durable runtime

This distinction is easy to miss. A terminal UI can make a coding agent pleasant to use, yet still leave a long-running execution vulnerable to a laptop sleep, a process crash, or an approval that arrives hours later.

`decode` therefore has a separate headless runtime path. The normal interactive route is optimized for conversation. The durable route is optimized for execution that can be resumed, inspected, and replayed. It runs the same agent through Kitaru, a workflow runtime that checkpoints each model call and tool call.

That granularity matters. A single final transcript cannot tell the runtime where it is safe to continue. A checkpoint immediately before a model request can. If the worker stops there, recovery can reuse the earlier work and issue the pending request again; if an operator wants to test a model change, that same checkpoint is a precise fork point.

The practical workflow begins with a durable run:

```bash
uv run decode run "Inspect this repository and explain the test layout"
```

The command returns an execution identifier. Operators can use it to inspect the execution and its durable anchors:

```bash
uv run kitaru executions get <EXECUTION_ID>
```

For a real investigation, the identifier is not incidental metadata. It is the handle for the evidence we intend to compare.

## What is actually durable?

It is tempting to say that the runtime “saves the agent.” That is too vague to be useful. A model has no hidden, recoverable process state that the harness can simply serialize. What can be made durable is the execution boundary around it: the input to each model request, the tool call it selects, the observation returned by that tool, and the control-flow point at which the runtime knows that work completed.

That yields a more precise architecture:

```text
request
  │
  ▼
durable workflow ──► model-request checkpoint ──► model
  ▲                                                    │
  │                                                    ▼
  └── tool-result checkpoint ◄── tool call ◄── decision
```

The checkpoints are not a debugging afterthought bolted onto a chat transcript. They are the workflow’s source of truth. If a model call completed, the runtime knows that. If a tool observation was recorded, a replay can use it instead of guessing at an earlier machine state. If a boundary has not completed, the runtime knows precisely what needs to happen next.

This is why the location of a checkpoint matters more than the existence of a log file. An anchor immediately before a model request gives an operator a meaningful choice: repeat the same decision under the same configuration, or swap the active model and observe a new decision. An anchor after a destructive tool call would be much less useful for that question.

## From a command to an execution you can inspect

The lesson’s runnable path is intentionally short, but its semantics are not casual:

```bash
# Run the agent in the durable, headless path.
uv run decode run "Find the relevant test, make a minimal fix, and verify it"

# Inspect the durable execution and identify its call anchors.
uv run kitaru executions get <EXECUTION_ID>

# Establish that replay itself is stable.
uv run decode replay <EXECUTION_ID> --from decode_runtime_model_request

# Fork the same evidence with a candidate model.
uv run decode replay <EXECUTION_ID> \
  --from decode_runtime_model_request \
  --model gemini-2.5-pro
```

The first run creates the evidence. The second is the baseline. The third changes one explicitly named variable.

There is a subtle but important distinction here: the runtime is not promising that two model calls will produce identical language. It is making the experimental setup inspectable. If the baseline differs unexpectedly, that is information about the environment, sampling, or replay contract. If the candidate differs after a clean baseline, that difference is much easier to attribute and investigate.

## Replay is a fork with caching rules

The replay command is deliberately thin:

```bash
uv run decode replay <EXECUTION_ID> \
  --from decode_runtime_model_request \
  --model gemini-2.5-pro
```

The anchor names the durable call boundary, not a vague instruction such as “start near the middle.” Work upstream of the anchor is replayed from recorded results. Work downstream is executed again. The new model receives the inherited conversation state and makes the next decision from there.

This also defines the limits of the guarantee. Replay preserves the recorded prefix; it does not make downstream reality deterministic. A new model may choose a different tool. A downstream command may read changed files or perform a real side effect. That is why replay belongs with an explicit execution boundary and a controlled workspace, not as an excuse to rerun unbounded host commands.

There are two other constraints worth stating plainly:

- A model override applies to the configured active provider; it is not a promise of arbitrary cross-provider migration.
- Human-in-the-loop approvals are not silently recycled. In the local setup, replay can wait for a fresh answer rather than pretending an earlier approval applies to a changed execution.

Those restrictions are not missing polish. They preserve the meaning of the experiment.

## A concrete failure that replay can isolate

Imagine the observed agent has already inspected the repository and found a failing test. Its next model call decides whether to make a focused change or to edit several unrelated files. The investigation is not “which model produces nicer prose?” It is whether the next decision, given the same evidence, respects the task boundary.

With an ordinary rerun, a candidate model might discover a different file order, issue a different exploratory command, and arrive at an apparently better result for an unknowable reason. With a replay anchor immediately before the decision, both branches inherit the test output and repository observations already recorded. We can then inspect:

- the exact messages and tool results supplied to the model;
- the tool call each branch selected after the anchor;
- the files and tests affected by downstream work; and
- the final task outcome, assessed by the project’s own verification.

That is a small experiment, not a leaderboard. It tells us where to look when a branch diverges: context construction, model behavior, tool policy, environmental state, or the task evaluator.

## The baseline run is part of the experiment

The most common replay mistake is comparing the original execution directly with a model-swapped fork. That comparison is useful for debugging, but it cannot separate model behavior from replay mechanics.

A stronger model-change investigation uses three runs:

1. **Observed run:** capture the original execution and select a checkpoint anchor.
2. **Baseline replay:** replay from that anchor with the original configuration, without a model override.
3. **Model fork:** replay from the same anchor with the candidate model.

```text
                         replay: same configuration
observed execution ─────────────────────────────────► baseline
          │
          └──────────── replay: model override ─────► candidate fork
```

Now the comparison has two purposes. The baseline tells us whether the replay path itself behaves as expected. The candidate fork tells us what changed when the selected model changed. A different result is not automatically a defect; it may be the signal we were looking for. The important thing is that we can locate the changed variable and inspect the inherited context.

## A checkpoint is an operational contract

At first, checkpointing sounds like a storage detail: write an event log or save a blob somewhere. In a coding agent it becomes a behavioral contract between the model loop, tools, runtime, and operator.

The contract needs to answer concrete questions:

- What model request or tool call has definitely completed?
- Which observations are safe to reuse?
- What is allowed to run again after the anchor?
- Where can an operator inspect the execution before taking action?
- How do tests verify the recovery and replay path?

The canonical project treats these as architecture rather than as logging. Its runtime lesson ships a runnable demonstration, while its integration suite includes an end-to-end capstone test for the runtime contract. This is exactly the point where an agent project stops being a collection of promising scripts and starts behaving like a system with operational semantics.

The companion repository’s Week 3 lab remains useful for learning the smaller pieces: rebuilding history from persisted events, protecting source artifacts from mutation, and producing comparison reports. But those are teaching artifacts, not a claim that a JSONL demo is equivalent to a durable workflow engine. Keeping that distinction explicit has made this series more honest—and more useful.

## The tests have to prove the boundary, not the model

The difficult part to test is not whether a model is intelligent. That is a task-and-evaluation question. The runtime contract is more concrete:

- a completed call is checkpointed before the next dependent work begins;
- recovery continues from a known durable boundary;
- replay reads the selected upstream results rather than executing them again;
- the model override is routed only through supported provider configuration; and
- the end-to-end runtime flow remains executable as the agent changes.

These are the kinds of assertions that make an operational claim credible. A screenshot of a chat completing once is encouraging; it is not evidence that the agent can resume after a worker failure or fork from a named anchor. The canonical integration test is valuable because it exercises the public runtime path rather than only a helper function in isolation.

For an engineering team, this also changes the review conversation. A proposed feature no longer needs to be assessed solely by reading agent prompts. Reviewers can ask what is durable, what gets re-executed, which side effects are possible after an anchor, and which test captures the intended behavior.

## What replay does not evaluate for us

Replay creates evidence; it does not declare a winner.

A candidate model that uses fewer tools may be efficient, or it may have skipped the investigation needed for a safe change. A shorter answer may be clearer, or it may omit the crucial caveat. Token counts and elapsed time are measurements. Correctness still comes from task-specific tests, review, and eventually a deliberate evaluation suite.

Equally, replay is not containment. If downstream work can write files, invoke networked tools, or otherwise affect the environment, those effects need their own permission and sandboxing policy. That is the subject of the next installment.

## The larger lesson

Week 1 made the agent loop visible. Week 2 made its state survivable. Week 3 makes an execution inspectable and falsifiable.

That sounds abstract, but it changes the development posture. Instead of responding to a surprising agent decision with prompt folklore or a brand-new run, we can preserve the observed state, fork at a named boundary, hold the configuration steady, change one variable, and compare the results.

The model is still important. The difference is that improving the agent no longer has to be guesswork. It can be systems engineering.

Next, I will take on the safety boundary that this runtime deliberately does not solve: permission is not containment, and a coding agent that can execute commands needs both.

---

*This is Week 3 of my “Building a Coding Agent From Scratch” series. Read the [canonical durable-runtime lesson](https://github.com/silsgah/building-a-coding-agent-from-scratch-course/tree/master/lessons/03-durable-runtime), or explore the [companion Week 3 lab](https://github.com/silsgah/coding-agent-course/tree/master/week-03-replay-model-swap).*
