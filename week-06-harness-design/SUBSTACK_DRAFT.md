# Building a Coding Agent From Scratch, Week 6: Make the Harness Read Like Software

### The model may choose an action, but the agent’s state, tools, schemas, and tests should still be ordinary code a teammate can inspect.

By Week 5, the agent in this series could manage context, retain scoped memory,
and retrieve a focused symbol instead of an entire file. The harness was more
capable—but also at risk of becoming a collection of separate registries,
prompts, schemas, and dispatch functions.

Week 6 applies a deliberately simple design constraint: represent the agent as
a Python object. Its fields are state. Its public decorated methods are tools.
Its class docstring is the stable system instruction. The goal is not a magic
framework. It is to put behavior that changes together in one reviewable unit.

This is Week 6 of my *Building a Coding Agent From Scratch* series. It builds
on the tool loop, durable history, replay, containment, and context controls by
making the harness easier to evolve without losing its contracts.

The code is in the [course repository](https://github.com/silsgah/coding-agent-course/tree/master/week-06-harness-design).

## A method is the source of truth for a tool

In an early agent, adding a tool can require updating a Python function, a
separate JSON schema, a dispatcher, and a prompt. Those copies eventually
drift. The Week 6 `CodingAgent` marks model-callable methods with a small
decorator:

```python
@tool
def read_file(self, path: str) -> str:
    """Read one UTF-8 text file relative to the workspace."""
    ...
```

At runtime, the harness discovers decorated methods and derives OpenAI-style
tool schemas from the method name, signature, type hints, defaults, and first
docstring sentence. The same signature validates model-supplied arguments
before dispatch.

That gives one source of truth for three things that must agree: what a tool is
called, what inputs it accepts, and how it is described to the model.

## State becomes inspectable too

The object owns its history, provider, workspace, tool-call count, and token
count. A run is still the familiar ReAct cycle, but it is now a method over
well-defined state:

```text
CodingAgent
├── history
├── provider
├── configured workspace
├── decorated tool methods
└── stats()
```

That structure makes tests straightforward. A test can construct an agent with
a temporary workspace and scripted provider, call `run()`, then inspect the
resulting history and immutable `AgentStats`. It does not need a live API,
global registry, or a monkey-patched command line.

The same approach makes code review more honest. A reviewer can see what
capabilities the agent exposes by reading a single class rather than inferring
them from a prompt and several registries.

## Tool ergonomics are not a security boundary

The object includes useful defensive controls: workspace-contained paths,
limited file and command output, argument validation, a 10-iteration limit,
and rejection of shell composition plus a small destructive-command blocklist.

Those controls prevent common accidents. They do not make a host process safe
to expose to untrusted tasks. A blocklist will never enumerate every dangerous
program, and a command that is harmless in one repository can be harmful in
another. The correct production composition remains: this object defines the
agent interface; Week 4’s sandbox limits the executor’s authority.

## Benchmark the harness contract, not model mythology

The lesson’s `refactor_demo.py` and `benchmark.py` are deterministic offline
comparisons. The benchmark uses a scripted provider to exercise the full
provider → method → tool result → final answer sequence. It can measure the
harness path and catch a regression in schema discovery or dispatch.

It is not evidence that one live model is more intelligent, cheaper, or more
reliable than another. Those claims require representative tasks, fixed
conditions, repeated runs, and a separate evaluation methodology—the focus of
Week 8.

## What I tested

Six offline tests verify that the object harness derives schemas from decorated
methods, records the complete model → tool → result → answer cycle, returns
controlled errors for unknown tools and invalid arguments, prevents workspace
escapes, rejects shell composition and selected destructive commands, and runs
the refactor comparison and scripted benchmark without an API key.

Run them from the repository root:

```bash
python -m unittest discover -s week-06-harness-design/tests -v
```

## The useful abstraction is the boring one

An agent need not be mysterious to be capable. When tools are methods, state is
visible, schemas are derived, and execution is injected, the harness becomes
ordinary software with ordinary tests and review points.

That is the leverage in Week 6. The model remains important, but its behavior
is now surrounded by a structure a team can reason about, version, and improve.

Next, the course asks what happens when one well-bounded agent is not enough:
how to split independent work among parallel children without multiplying
authority, cost, and confusion.

---

*This is Week 6 of my “Building a Coding Agent From Scratch” series. The
project now represents an agent as a testable Python object with derived schemas
and explicit execution boundaries.*
