# I Built a Time Machine for My Coding Agent

Most agent debugging still looks like archaeology: an agent makes a strange choice, we read a long log, and we guess what went wrong. This week I built a more useful tool: a replay harness that forks an agent from an exact checkpoint and asks a different model to continue from there.

The idea is simple. Week 2 of my coding-agent course stored every important action in an append-only checkpoint log: the user request, each tool call, the tool result, and a marker that the step completed. Week 3 uses that log as a branching point.

Instead of rerunning the whole task and hoping the same early decisions happen again, I can say: “Keep everything through tool step two. Now let another model take over.” The original run remains untouched. The new branch copies the inherited event prefix, records replay metadata, and writes every new event to its own checkpoint.

## Why that distinction matters

Re-running from scratch answers a fuzzy question: “How does another model behave on a similar prompt?” Replay answers a controlled question: “Given this exact conversation and these exact tool results, what does another model do next?”

That makes it useful for three jobs:

- Debugging: bisect an unsuccessful run to find the first bad decision.
- Evaluation: compare models with the same context and tool access.
- Cost analysis: record prompt tokens, completion tokens, tool-call count, and wall-clock time alongside the answer.

The output is deliberately boring and inspectable: JSONL checkpoints plus a small `run_metrics.json` file. From any set of runs, a report command produces a Markdown table and places the final answers side by side for human review.

## The workflow

First I run a task and save its checkpoint:

```bash
python code/replay_harness.py --task "List the files here and create a summary.md"
```

Then I branch it at a completed tool step with two models:

```bash
python code/model_swap.py --original sessions/run-... \
  --from-step 1 --models gemini-2.0-flash gpt-4o-mini
```

Finally I generate a report:

```bash
python code/comparison_report.py --runs sessions/swap-... sessions/swap-...
```

The report is not an automatic quality judge. That is intentional. Token counts, cost, latency, and tool-call efficiency are objective; whether an answer is actually good still needs a task-specific evaluator or a human. The harness makes that comparison easy to inspect rather than pretending that the cheapest answer is necessarily the best one.

## The lesson I’m taking forward

The model is only one variable in an agent system. A checkpoint format, replay semantics, tool permissions, sandboxing, and evaluation are what make an agent debuggable. Once the run is recorded as a sequence of durable events, it becomes an experiment you can reproduce—not a one-off conversation that disappeared into a log.

Next, I want to extend this into an automated replay suite: a list of tasks, a set of models, and a CSV/Markdown report that can catch regressions before a harness change ships.

*This is Week 3 of my “Building a Coding Agent From Scratch” project: replay and model-swap experiments.*
