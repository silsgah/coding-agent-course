# Week 3 — Exercises

## Exercise 1: Bisect a bad decision
1. Run a multi-step task that produces a suboptimal answer
2. Use `replay_harness.py` to fork from different steps
3. Find the exact step where the model went wrong
4. Replay from that step — does a different model do better?

## Exercise 2: Temperature experiments
Modify `model_swap.py` to compare the same model at different temperatures (0.0, 0.5, 1.0). Which produces the best answers? Which is most consistent?

## Exercise 3: Cost calculator
Add a cost estimation to `comparison_report.py` based on per-token pricing:
- Gemini Flash: ~$0.075/1M input, ~$0.30/1M output
- GPT-4o-mini: ~$0.15/1M input, ~$0.60/1M output
- Claude Haiku: ~$0.25/1M input, ~$1.25/1M output

## Exercise 4: Automated replay testing
Build a script that takes a list of tasks, runs each with multiple models, and produces a CSV report. This is your first step toward systematic evaluation (Week 8).

## Exercise 5: Checkpoint diff tool
Build a tool that takes two checkpoint files and shows:
- Where the runs diverge
- What each model chose differently
- Token cost difference at each step
