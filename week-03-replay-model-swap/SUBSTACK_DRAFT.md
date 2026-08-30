# Building a Coding Agent From Scratch, Week 3: Replay the Decision, Not the Whole Run

### A checkpoint is more than crash recovery. It is the point from which you can ask a controlled “what if?” question.

Last week, I made my coding agent survive interruption. Every important action—a user request, a model-selected tool call, the tool’s result, and the completion marker—is written to an append-only JSONL checkpoint. If the process dies, the agent can rebuild its conversation and continue without redoing finished work.

That solved a reliability problem. This week, I am using the same record to solve a debugging problem.

When an agent makes a bad decision, the obvious response is to start another run with another model. But that does not tell us much. The second model receives the original prompt, then makes its own early choices, sees different tool output, and reaches a different state. The two runs are no longer answering the same question.

The question I actually want to ask is narrower:

> Given this exact task, conversation, and set of observed tool results, what would another model do next?

That is what the Week 3 replay harness does. It forks an existing agent run at a completed step, preserves the original evidence, and lets a new branch continue from the same state. The model can change. The inherited history cannot.

This is the third installment in my *Building a Coding Agent From Scratch* series:

1. **Week 1 — The bare agent loop:** model → tool call → observation → next step.
2. **Week 2 — Resumability and checkpoints:** persist that loop so a crashed run can resume.
3. **Week 3 — Replay and model swaps:** branch a recorded run to debug and compare decisions.

The code for this lesson is in the [course repository](https://github.com/silsgah/coding-agent-course/tree/master/week-03-replay-model-swap).

## The failure mode: “just run it again” is not an experiment

Consider a simple coding task: inspect a repository, identify the relevant files, make a change, then run the tests. Assume the original agent has already listed the files and read the configuration. On its next turn, it chooses an unhelpful command.

If I restart from the initial prompt with another model, I cannot tell whether a better outcome came from the new model or from a different directory listing, a different file read, or a different first plan. I changed too many variables at once.

Replay fixes the boundary. The original run stays intact; the branch inherits only the events up to the selected completed tool step:

```text
Observed run                         Replay branch

user request                         user request          (inherited)
tool call: list files                tool call: list files (inherited)
tool result: repository contents     tool result: ...      (inherited)
step 1 complete                      step 1 complete       (fork point)
tool call: wrong command             model B decides next  (new)
...                                  ...
```

The model sees the same information at the fork point. The branch records a new decision sequence beside the original one. That makes divergence visible and attributable.

## The runtime contract from Week 2

The replay harness works because the Week 2 checkpoint is an event log, not a loose collection of console output. One JSON object is appended for each meaningful event:

```json
{"event_type":"user_message","data":{"message":"Inspect this project"}}
{"event_type":"tool_call","data":{"tool_name":"bash","arguments":{"command":"ls"}},"step_id":"step-1"}
{"event_type":"tool_result","data":{"tool_name":"bash","result":"README.md\nsrc"},"step_id":"step-1"}
{"event_type":"step_complete","data":{"completed":true},"step_id":"step-1"}
```

This distinction is important. A model API call is stateless from the harness’s perspective: the next request succeeds only because the harness sends a history containing the previous messages and tool observations. The durable artifact must therefore be the context needed to reconstruct that history—not an attempt to save invisible model state.

For replay, a completed tool step is a useful boundary because it includes both sides of an action: what the model requested and what the environment returned. Forking after a request but before its result would leave an unresolved tool call in the message history and make the state ambiguous.

## Forking a run, event by event

The core of the implementation is deliberately small. First, I select the exact event prefix ending at the requested completed step:

```python
def events_through_step(events, completed_steps):
    if completed_steps == 0:
        return [event for event in events
                if event["event_type"] == "user_message"][:1]

    prefix, seen_steps = [], 0

    for event in events:
        if event["event_type"] == "assistant_response":
            break
        prefix.append(event)
        if event["event_type"] == "step_complete":
            seen_steps += 1
            if seen_steps == completed_steps:
                return prefix

    if completed_steps > seen_steps:
        raise ValueError("Requested replay step does not exist")
    return prefix
```

The branch copies that prefix into its own checkpoint file, adds explicit replay metadata, rebuilds the conversation, and resumes the normal tool loop:

```python
prefix = events_through_step(events, from_step)
writer = CheckpointWriter(target_dir)
copy_event_prefix(prefix, writer)

writer.write(CheckpointEvent(
    event_type="replay_metadata",
    data={
        "source_session": str(source_dir.resolve()),
        "from_step": from_step,
        "model": model,
    },
    step_id="replay",
))

history = history_from_events(prefix)
await continue_run(history, writer, model)
```

Two design choices are doing most of the work here.

First, the source session is immutable. A replay cannot accidentally rewrite the evidence it is meant to examine. Second, the branch contains its inherited prefix instead of merely pointing at it. That makes the branch portable and replayable in its own right; a report can inspect one directory and see the full state the model received.

`--from-step 0` is also intentional: it preserves the user request but none of the original model’s choices. Larger values fork after that many completed tool calls. If the requested step is unavailable, the harness fails loudly rather than silently running from the wrong point.

## One checkpoint, multiple model branches

The model-swap runner applies the same fork operation once per model:

```bash
python code/model_swap.py \
  --original sessions/latest \
  --from-step 1 \
  --models gemini-2.0-flash gpt-4o-mini
```

This produces a separate session directory for each candidate. The harness does not need to know whether the chosen model comes from Gemini, OpenAI, OpenRouter, or another compatible provider. It asks the shared provider layer for a model, sends the reconstructed messages and tool schemas, and records the resulting events.

That separation is the architectural point. The agent loop should not be rewritten because the model changed. Model selection is an input to the experiment, not a fork of the harness code.

Of course, a model swap alone does not make an experiment perfectly deterministic. Sampling settings can vary; external tools can return different data; and a command that writes to disk has a real side effect. The replay harness isolates the *recorded context* and model choice. Week 4’s sandboxing work is the complementary control: it will constrain where those replayed tools are allowed to act.

## Record the evidence, then judge it

Each completed branch writes a compact `run_metrics.json` alongside its checkpoint. It captures the model name, prompt tokens, completion tokens, tool-call count, elapsed time, final answer, and any error. The comparison tool turns multiple branches into a Markdown report:

```bash
python code/comparison_report.py \
  --runs sessions/swap-gemini-2-0-flash sessions/swap-gpt-4o-mini \
  --output comparison_report.md
```

The report puts the operational facts in one table and then prints the final answers side by side. For supported model families, it can also estimate token cost using configured per-million-token rates.

This is intentionally not an automatic quality verdict. A branch with fewer tool calls might be efficient—or it might have skipped the investigation required to answer correctly. A lower token count is not evidence of a better fix. The job of this layer is to preserve and organize evidence. Task-specific tests, human review, and later evaluation infrastructure decide whether a result is actually good.

That separation is easy to overlook when building agents. Metrics are measurements, not conclusions.

## Testing the replay contract without calling a model

Before comparing live models, I added an offline test suite around the behavior that must not change. The six tests cover:

- parsing a checkpoint and rejecting malformed JSON with its line number;
- reconstructing history through a valid fork boundary;
- rejecting a missing replay step;
- preserving only the user request at step zero;
- generating a comparison report and cost estimate; and
- simulating a branch to verify that inherited events, replay metadata, a new answer, and persisted token metrics all end up in the correct session.

The tests are not evaluating model intelligence. They are verifying the harness invariant that makes model evaluation possible: a branch must preserve the right state, without mutating the original run.

## The larger lesson

In Week 1, an agent could act. In Week 2, it could survive interruption. In Week 3, its decisions become inspectable experiments.

That is a meaningful shift. A bad run is no longer only a transcript to read after the fact. It becomes a reproducible starting point: hold the observed state constant, change one variable, and see where behavior diverges.

The model still matters. But once the harness can preserve state, isolate a fork boundary, and compare branches honestly, the work of improving an agent starts to look less like prompt folklore and more like systems engineering.

Next week, I will address the risk that has been present since the first `bash` tool call: how to let an agent execute useful commands without handing it unrestricted access to the machine running it.

---

*This is Week 3 of my “Building a Coding Agent From Scratch” series. Week 1 built the agent loop; Week 2 added durability; Week 3 turns durable runs into replayable experiments.*
