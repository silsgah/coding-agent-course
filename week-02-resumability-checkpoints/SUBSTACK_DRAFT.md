# Building a Coding Agent From Scratch, Week 2: A Checkpoint Is a Recovery Contract

### A long-running agent does not become durable because it writes a transcript. It becomes durable when a restart can reconstruct a valid next decision without pretending that unfinished work completed.

Last week, I built the smallest useful coding-agent loop: a model proposes a
tool call, a human approves or denies it, the harness returns the observation,
and the model continues. That is enough to answer a question interactively.
It is not enough to survive a process dying halfway through a task.

Consider an agent that has inspected a repository, written part of a plan, and
is about to run a test command when the machine is restarted. If the only
record is terminal output, the next process has to guess what happened. It may
repeat expensive exploration, send an invalid tool history to its model API, or
claim a step finished when it did not.

Week 2 adds a durable boundary around the Week 1 loop: an append-only event log
that records the conversation and tool lifecycle as it occurs. On restart, the
harness replays that log into the exact history the next model request needs.

This is the second installment in my *Building a Coding Agent From Scratch*
series:

1. **Week 1:** a human-approved model → tool → observation loop.
2. **Week 2:** a durable event log and safe restart behavior.
3. **Week 3:** replaying a recorded run to compare decisions and models.

The Week 2 code is available in the
[course repository](https://github.com/silsgah/coding-agent-course/tree/master/week-02-resumability-checkpoints).

## The unit of durability is an event, not a console line

The checkpoint is a JSONL file: one JSON object per line, appended in the order
events occur. For a simple tool action, the useful sequence is:

```text
user_message
tool_call
tool_result
step_complete
assistant_response
```

For example:

```json
{"event_type":"user_message","data":{"message":"Inspect the project"}}
{"event_type":"tool_call","data":{"tool_name":"read_file","arguments":{"path":"README.md"}},"step_id":"readme-1"}
{"event_type":"tool_result","data":{"tool_name":"read_file","result":"..."},"step_id":"readme-1"}
{"event_type":"step_complete","data":{"completed":true},"step_id":"readme-1"}
```

This sequence preserves two different facts that a transcript often blurs:
what the model *requested* and what the environment *returned*. The distinction
is what lets the runtime rebuild a tool-aware conversation without invoking the
tool again.

The writer appends each event with UTF-8 encoding, flushes it, and calls
`fsync` before returning. That makes the lesson’s durability boundary concrete:
when a tool result has been recorded, the harness has made a synchronous effort
to persist the observation before it asks the model for another decision.

## The hard case: the crash between intent and result

The most revealing failure window occurs after the harness writes a `tool_call`
event but before there is a corresponding `tool_result` event. The process may
die at exactly that point. The log correctly says the model proposed an action,
but it cannot prove that the action completed.

Sending that unresolved call back to a tool-aware provider is invalid: the
assistant’s tool request must be followed by a matching tool result. The
reader therefore removes a *trailing* unmatched tool-call message while it
rebuilds history:

```python
while (
    state.messages
    and state.messages[-1].get("role") == "assistant"
    and state.messages[-1].get("tool_calls")
):
    state.messages.pop()
```

The important word is *trailing*. Completed earlier steps remain in history.
Only the last incomplete proposal is removed, allowing the resumed model to
decide the next action from a valid conversation. This is better than silently
inventing a tool result, and better than reusing a malformed history.

There is a limit that should not be hidden. If a tool changes the outside world
and the process crashes after that change but before the result is persisted,
the event log cannot know whether the side effect happened. Removing the
unresolved request lets the model reconsider; it does not provide exactly-once
execution.

Production tools that create tickets, charge money, deploy code, or modify a
database need an additional protocol: an idempotency key, a durable external
operation identifier, a read-after-write check, or a compensating action. The
checkpoint makes the ambiguity visible. It does not erase it.

## A corrupt log should fail usefully; a torn final append is different

A second recovery decision is easy to miss. A checkpoint might contain invalid
JSON because a crash interrupted the final write. The reader distinguishes that
case from corruption in the middle of history.

- A malformed final non-empty line is treated as a torn append and ignored.
  All prior valid events can still be replayed.
- A malformed earlier line, unknown event type, missing required field, or bad
  tool-argument shape raises a `CheckpointFormatError` with the line number.

That policy is intentionally conservative. Continuing past corrupted
intermediate history could cause later events to be interpreted against the
wrong state. Failing with an actionable location gives an operator a record to
inspect instead of producing a plausible but unreliable resumed run.

## Replay is a reconstruction, not another model call

On restart, `CheckpointReader` turns durable events back into the provider
message shape. A saved `tool_call` becomes an assistant message with a tool-call
identifier; its `tool_result` becomes the matching tool message. A saved final
answer becomes an assistant message. The model itself remains stateless—the
checkpoint is the harness-owned context that lets a fresh model request pick up
where the old process left off.

This is why event design matters so much. Week 3 will reuse the same record to
fork a run after a completed tool step. Rather than starting a different model
from the original prompt and changing every early decision, the replay harness
will hold observed history constant and ask: given this exact evidence, what
would another model do next?

## What I tested

The Week 2 recovery suite runs without an API key or a live model. Its six
tests cover:

- reconstructing a complete user → tool → result → answer conversation;
- loading an empty session safely;
- retaining completed work while removing an interrupted trailing tool request;
- ignoring a torn final JSONL record;
- reporting malformed earlier JSON with its line number; and
- rejecting structurally incomplete events with an actionable error.

Run it from the repository root:

```bash
python -m unittest discover -s week-02-resumability-checkpoints/tests -v
```

The interactive examples remain model-backed, because their job is to show a
live agent acting through the durable loop. The recovery contract itself does
not need a provider to be tested, which keeps the critical behavior repeatable
and inexpensive to verify.

## From an agent that acts to an agent whose work can be trusted

Week 1 established the decision loop. Week 2 asks a systems question: after an
interruption, what evidence may the next decision trust? The answer is not
“everything printed before the crash.” It is the durable record of completed
observations, plus explicit handling for the work whose outcome is unknown.

That is the foundation for the next capability. Once a run can be reconstructed
without mutating the original evidence, it can be replayed, branched, and
compared. A checkpoint stops being only crash recovery; it becomes the first
artifact of an evaluation harness.

---

*This is Week 2 of my “Building a Coding Agent From Scratch” series. The
project now uses an append-only, synchronously persisted event log with
validated replay and explicit recovery boundaries.*
