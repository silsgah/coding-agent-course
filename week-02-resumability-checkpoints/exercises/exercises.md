# Week 2 — Exercises

## Exercise 1: Inspect the checkpoint log

Run `durable_runtime.py`, perform a few operations, then:
1. Open `sessions/interactive/checkpoint.jsonl` in your editor
2. Read each line — can you trace the exact sequence of events?
3. How would you recover the conversation from just this file?

---

## Exercise 2: Manual crash recovery

1. Run `durable_runtime.py` and give it a multi-step task
2. Press `Ctrl+C` mid-execution (real crash!)
3. Run `durable_runtime.py` again — does it resume correctly?
4. Check: were any tool calls repeated?

---

## Exercise 3: Add checkpoint metadata

Extend `CheckpointEvent` to include:
- `model_name` — which model generated the tool call
- `token_count` — tokens used for this step
- `elapsed_seconds` — wall-clock time for this step

This metadata becomes essential for cost tracking (Week 5) and evaluation (Week 8).

---

## Exercise 4: Checkpoint compression

After 50+ events, the checkpoint file gets large. Implement a `compact()` method that:
1. Reads all events
2. Removes duplicate or superseded events
3. Writes a compacted version

**Think about:** What events can safely be removed? What must be kept?

---

## Exercise 5: Multiple sessions

Modify the runtime to support multiple named sessions:
```bash
python durable_runtime.py --session "fix-login-bug"
python durable_runtime.py --session "add-tests"
```

Each session gets its own checkpoint file and can be resumed independently.

---

## Solutions

### Exercise 3 — Checkpoint metadata

```python
@dataclass
class CheckpointEvent:
    event_type: str
    data: dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    step_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    # New fields:
    model_name: str = ""
    token_count: int = 0
    elapsed_seconds: float = 0.0
```
