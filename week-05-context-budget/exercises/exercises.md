# Week 5 — Exercises

## Exercise 1: Write an AGENTS.md for a real project
Pick a project you work on and write an AGENTS.md for it. Include coding conventions, test commands, architecture, and things to avoid. Test it: does the agent follow your instructions?

## Exercise 2: Compaction quality test
Run a long conversation (20+ turns) with compaction enabled. After compaction, ask the agent about something from the beginning. Does it remember? Adjust `keep_recent` and compare.

## Exercise 3: Write a custom skill
Create a skill for a domain you know well (e.g., React patterns, SQL optimization, Docker commands). Load it and test: does the agent use the knowledge correctly?

## Exercise 4: NOOA token comparison
Run the same 10-step task with:
1. Your compaction approach (compact at 80%)
2. Breaking the task into 10 separate single-step calls (NOOA-style)
Compare total tokens used. Which approach is cheaper?

## Exercise 5: Dynamic skill loading
Modify the agent to detect what the user is working on (Python? TypeScript? Docker?) and automatically load the relevant skill. Use file extensions as the trigger.

## Solutions

### Exercise 4 hint:
```python
# NOOA-style: each step is a fresh context
total_tokens = 0
for step in steps:
    response = await provider.chat([
        Message(role="system", content=SYSTEM_PROMPT),
        Message(role="user", content=step),
    ])
    total_tokens += response.usage["prompt_tokens"] + response.usage["completion_tokens"]

# vs. traditional: growing history with compaction
# (use context_budget.py as-is)
```
