# Week 6 — Harness Design as the Real Lever (Full NOOA Module)

> The same underlying model, wrapped in different harnesses, produces double-digit swings in benchmark results — and even bigger swings in token cost.

---

## Learning Objectives

By the end of this week, you will:
1. Understand NOOA's core mental model: **an agent as a plain Python object**
2. Refactor your Week 1–4 agent using the **agent-as-object pattern**
3. Compare **methods-as-tools** vs traditional tool schemas
4. **Benchmark** token cost and reliability before and after

## The Big Idea

This is the week where the course thesis lands. You've built an agent over 5 weeks. Now we show you that the *same model*, wrapped differently, performs dramatically differently.

NVIDIA's NOOA framework demonstrates this with a radical simplification:

> **An agent is a Python object. Methods are actions. Fields are state. Docstrings are prompts. Method bodies — when left as `...` — are completed by an LLM. Everything else stays ordinary Python.**

This means:
- Adding a tool = adding a method (no schema, no registration)
- Testing an agent = testing a class (`pytest`)
- Code-reviewing an agent = reading a Python file (no prompt chains to trace)
- Version-controlling an agent = `git diff` (no hidden config)

## NOOA Design Principles

### 1. Methods as tools
```python
# Traditional approach (Week 1): separate schema + function
TOOL_SCHEMAS = [{"type": "function", "function": {"name": "get_stock", ...}}]
def get_stock(item: str) -> int: ...

# NOOA approach: the method IS the tool
class InventoryAgent(Agent):
    def get_stock(self, item: str) -> int:
        \"\"\"Get current stock for an item.\"\"\"
        return self.inventory.get(item, {}).get("stock", 0)
```

### 2. Docstrings as prompts
```python
# Traditional: separate system prompt string
SYSTEM_PROMPT = "You are a support agent. When creating tickets, include..."

# NOOA: the docstring IS the prompt
class SupportAgent(Agent):
    \"\"\"You are a support agent. When creating tickets, include...\"\"\"
    async def triage(self, message: str) -> Ticket:
        \"\"\"Create a typed support ticket from the customer message.\"\"\"
        ...  # LLM completes this
```

### 3. Strategies control execution
```python
@strategy(PredictStrategy())       # Fast: single-shot structured output
async def classify(self, text: str) -> str: ...

@strategy(CodeActStrategy())       # Powerful: iterative Python REPL
async def solve(self, problem: str) -> str: ...
```

## Code Walkthrough

### `agent_as_object.py` — The NOOA pattern demonstrated

A complete agent built using the NOOA mental model: class = agent, methods = tools, docstrings = prompts. Shows how this simplifies the code from Week 1–4.

### `refactor_demo.py` — Before/after refactoring

Takes the Week 1 agent and refactors it to the agent-as-object pattern. Side-by-side comparison of:
- Lines of code
- Token cost per task
- Testability (can you `pytest` it?)

### `benchmark.py` — Token cost & reliability comparison

Run the same set of tasks with:
1. Your Week 1–4 harness (traditional tools + schemas)
2. The refactored agent-as-object version

Measure: tokens used, errors encountered, answer quality.

---

## Run It

```bash
cd week-06-harness-design/code

# See the agent-as-object pattern
python agent_as_object.py

# Before/after refactoring comparison
python refactor_demo.py

# Benchmark
python benchmark.py
```

## Exercises

See [exercises/exercises.md](exercises/exercises.md)

## References

- [NOOA README](../../labs-OO-Agents/README.md) — Framework overview
- [NOOA Examples](../../labs-OO-Agents/examples/README.md) — Progressive tutorial
- [NOOA Paper](https://arxiv.org/abs/2607.20709) — Design principles and benchmark results
- [NOOA Quickstart: Methods as Tools](../../labs-OO-Agents/examples/README.md#step-3-your-methods-are-your-tools-sw1--sw3-interleaving)
- [NOOA Quickstart: Strategies](../../labs-OO-Agents/examples/README.md#step-4-choose-how-your-methods-think)

---

**Deliverable:** Refactor your Week 1–4 agent using the "agent as Python object" pattern, and benchmark token cost and reliability before/after.
