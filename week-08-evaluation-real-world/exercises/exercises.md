# Week 8 — Capstone Exercises

## The Capstone

This week's exercises ARE the capstone project. Pick one track:

### Track A: Close a Real GitHub Issue
1. Pick a real issue from one of your repos (or create one)
2. Use your agent (or agent swarm) to produce a solution
3. Benchmark: accuracy, token cost, reliability (run it 3 times)
4. Write up: which harness design choices mattered most?

### Track B: Agent vs Agent Shootout
1. Run the benchmark suite on 3 different models
2. Add 5 custom tasks relevant to your work
3. Compare: pass rate, token cost, wall-clock time
4. Write up: which model + harness combination wins, and why?

### Track C: Build a Specialized Agent
1. Pick a domain (DevOps, data analysis, documentation, etc.)
2. Build a specialized agent with custom tools and skills
3. Create a benchmark suite specific to that domain
4. Write up: what did you customize, and what was the ROI?

---

## Capstone Deliverable

Your final deliverable includes:
1. **Working code** — your agent, with all customizations
2. **Benchmark results** — pass rate, token cost, reliability numbers
3. **Write-up** (1-2 pages) — justifying your harness design choices:
   - Which permission mode did you use, and why?
   - Did you use compaction or NOOA-style method boundaries?
   - Single agent or swarm? When did each shine?
   - What was the most impactful design decision?

---

## Bonus: Regression Testing

Set up a CI pipeline that:
1. Runs the benchmark suite on every PR
2. Compares results against the main branch baseline
3. Flags any regressions (pass rate dropped, token cost increased >20%)
4. Blocks merge if critical benchmarks fail
