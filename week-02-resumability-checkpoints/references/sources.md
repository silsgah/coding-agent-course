# Week 2 — References

## From the reference repos

### DecodingAI: Building a Coding Agent From Scratch
- **Lesson 3 — Durable Runtime:** `kill -9` resume, durable HITL waits, what-if replay
  Source: `src/decode/runtime/` — Kitaru durable flow
- **runtime.md:** Headless runs, durable checkpoints, human-in-the-loop waits, model-swapped replay
  See: `running_the_code/runtime.md`
- **Session format:** `src/decode/context/` — conversation log in JSONL

## Design patterns

| Pattern | Description |
|---|---|
| **Append-only log** | Write events sequentially; never modify past events. Simplest durable storage. |
| **Event sourcing** | Rebuild state by replaying events from the beginning. No separate "state" table. |
| **Write-ahead log** | Log the intent before execution. If the process crashes after logging but before executing, the resume path knows what was planned. |

## Articles

| Article | Why read it |
|---|---|
| [Kitaru on GitHub](https://github.com/zenml-io/kitaru) | The durable runtime used by DecodingAI's agent |
| [Event Sourcing (Martin Fowler)](https://martinfowler.com/eaaDev/EventSourcing.html) | The pattern behind our checkpoint design |
