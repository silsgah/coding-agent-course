# Week 7 — Exercises

## Exercise 1: Limit concurrency
Modify the swarm to cap at 3 concurrent children using `asyncio.Semaphore`. Compare wall-clock time with and without the cap.

## Exercise 2: Child agent specialization
Instead of giving every child the same tools, specialize them:
- "File explorer" child: only read_file and list_files
- "Code analyzer" child: read_file and bash (for grep/ag)
- "Writer" child: write_file

## Exercise 3: NOOA-style single agent comparison
Run the same task as a single agent processing subtasks sequentially. Compare total tokens, time, and answer quality against the swarm. Document when each approach wins.

## Exercise 4: Retry failed children
If a child fails (status="failed"), automatically retry it once with a higher token budget. Track how often retries succeed.

## Exercise 5: Hierarchical fan-out
Build a two-level hierarchy: coordinator → team leads → workers. The coordinator splits into high-level themes, each team lead splits further into specific tasks. When is this useful? When is it overkill?
