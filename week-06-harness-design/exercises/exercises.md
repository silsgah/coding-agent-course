# Week 6 — Exercises

## Exercise 1: Add a tool by adding a method
Add a `search_code(pattern: str, path: str = ".")` method to `CodingAgent`. Notice: no schema to update, no registry to modify. Just add the method and update `_get_tool_schemas()`.

## Exercise 2: Subclass for a specialized agent
Create a `PythonAgent(CodingAgent)` that adds Python-specific methods like `run_tests()`, `lint_code()`, and `format_code()`. The parent's tools are inherited automatically.

## Exercise 3: pytest your agent
Write unit tests for the agent's tool methods. These are just Python methods — they're testable with `pytest` like any other code. Test edge cases: nonexistent files, invalid commands, etc.

## Exercise 4: Token cost before/after
Run the same 5 tasks with both the Week 1 agent and the Week 6 agent. Compare total tokens. The agent-as-object approach should use fewer tokens because tool schemas are derived from docstrings.

## Exercise 5: Dynamic method addition
NOOA supports self-extending agents: the LLM can add new methods at runtime. Implement a simple version where the agent can define new helper functions during execution.
