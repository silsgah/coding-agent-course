# Building a Coding Agent From Scratch, Week 8: An Evaluation Is Evidence, Not a Vibe

### A green test suite proves that components meet their contracts. It does not prove that a coding agent completes representative work—or that a harness change made it better.

After seven weeks, this series has a real agent harness: a tool loop, durable execution, replay, workspace containment, context controls, an interaction model, and bounded parallel exploration. It would be tempting to call that finished.

It is not finished until we can answer a more difficult question:

> Did this change make the agent better, worse, or merely different?

That is what an evaluation system is for.

This final week is grounded in the canonical [`decode`](https://github.com/silsgah/building-a-coding-agent-from-scratch-course) project’s [evaluation lesson](https://github.com/silsgah/building-a-coding-agent-from-scratch-course/tree/master/lessons/07-evals), its [evaluation architecture decision record](https://github.com/silsgah/building-a-coding-agent-from-scratch-course/blob/master/docs/adr/0017-decode-eval-suite.md), and the operational [evaluation guide](https://github.com/silsgah/building-a-coding-agent-from-scratch-course/blob/master/running_the_code/evals.md). The lesson is not “add an LLM judge.” It is a layered evidence system: human demonstrations, outcome benchmarks, behavioral regression probes, and online evaluation over real traces.

## Series navigation

- [Week 1 — Why the Agent Loop is 20 Lines of Code](https://kwablagah.substack.com/p/why-the-agent-loop-is-20-lines-of?r=bpg99)
- [Week 2 — Your Coding Agent Has a Fatal Flaw](https://kwablagah.substack.com/p/your-coding-agent-has-a-fatal-flaw?r=bpg99)
- [Week 3 — Replay Is an Experiment, Not a Rerun](https://github.com/silsgah/coding-agent-course/tree/master/week-03-replay-model-swap)
- [Week 4 — Permission Is Not Containment](https://github.com/silsgah/coding-agent-course/tree/master/week-04-containment-sandboxing)
- [Week 5 — Context Is a Budget, Not a Memory Dump](https://github.com/silsgah/coding-agent-course/tree/master/week-05-context-budget)
- [Week 6 — The Harness Is the Product](https://github.com/silsgah/coding-agent-course/tree/master/week-06-harness-design)
- [Week 7 — Parallelism Is a Coordination Problem](https://github.com/silsgah/coding-agent-course/tree/master/week-07-parallel-subagents)
- **Week 8 — An Evaluation Is Evidence, Not a Vibe**

## Tests, benchmarks, and evals answer different questions

One of the most expensive mistakes in agent engineering is using one kind of evidence to answer every question.

| Evidence layer | The question it answers | Example |
| --- | --- | --- |
| Unit and integration tests | “Does the mechanism honor its contract?” | Does a denied tool request reach the executor? Does a replay preserve its anchor? |
| Outcome benchmark | “Can the agent complete this task?” | Can it repair a seeded bug in a fresh workspace? |
| Regression probe | “Did it work in the intended way?” | Did it use the right tool, respect a gate, preserve a fact through compaction, and keep the diff minimal? |
| Human demonstration | “Is this useful and convincing to a person?” | Can a reviewer inspect a real bug hunt or repository-analysis run? |
| Online evaluation | “Is live traffic still healthy?” | Do sampled production traces remain grounded and useful over time? |

These are not interchangeable.

A perfect unit suite cannot prove that a model can understand a realistic repository task. A benchmark pass cannot prove that the agent did not use an unsafe shortcut. A fluent LLM judge cannot replace a deterministic assertion that a file exists. And a demo that looks impressive once may be a lucky sample rather than a reliable capability.

The `decode` evaluation stack keeps these questions separate on purpose.

## The benchmark: outcome evidence in a controlled world

An outcome benchmark asks a simple question: did the agent complete the task?

Each benchmark task is a small world with a prompt, initial files, an isolated workspace, and a hidden oracle. The real agent works inside a fresh sandboxed workspace. Only after the run completes does the evaluator inject and execute `verify.sh` to return pass or fail.

```text
task fixture ──► fresh isolated Workspace ──► real agent run
                                                  │
                                                  ▼
                                       hidden verification oracle
                                                  │
                                                  ▼
                                              PASS / FAIL
```

The hidden oracle matters. If a model can read the grader, it can optimize for the grader instead of solving the task. That is why task assets distinguish the setup the agent may see from the verification code that arrives only after it stops.

Hidden does not mean mysterious. `verify.sh` is ordinary, readable grading logic, reviewed as part of the task. The suite includes oracle-sanity tests that prove both directions: a known correct solution passes, and the untouched fixture fails. Without those checks, an evaluation can become falsely reassuring because its verifier is broken or too permissive.

The evaluator uses the same sandbox executor seam as the agent rather than inventing another benchmark runner. A fresh Docker workspace is the normal local path; the remote sandbox backend can use the same interface. Reusing the production execution boundary means the benchmark measures the tool environment the agent actually uses.

## The regression suite: behavior evidence, not only outcomes

Two agents can both pass a task while behaving very differently. One may inspect the relevant files, obey a permission gate, and make a minimal change. Another may take a broad shortcut that happens to pass the fixture today and creates risk tomorrow.

Regression probes encode the harness behaviors we care about preserving. They can check, for example:

- that the agent uses a read tool instead of inventing repository facts;
- that a plan or permission boundary is honored;
- that compaction retains a critical earlier fact;
- that a change is minimal rather than a sprawling rewrite; and
- that a tool selection or final output meets a defined contract.

This is a different judgment surface from the benchmark. Benchmarks primarily ask about task outcome. Probes ask whether the architecture still behaves as designed after a model, prompt, tool, or runtime change.

The canonical project runs regression probes in temporary host-native directories so they are practical as a pre-merge engineering ritual. The threshold gate applies hard floors to metrics, while comparisons to a prior baseline begin as warnings rather than artificial hard failures on day one. That is a sensible adoption path: establish measured baselines before turning every natural variation into an incident.

## Deterministic metrics first; judges where code cannot decide

An LLM judge is useful for qualities that are difficult to express as a program: groundedness, completeness, reasoning quality, or whether a review explanation is genuinely helpful. It is not the right default for questions code can score exactly.

The evaluation design therefore uses two surfaces:

```text
Mechanical claim                    → deterministic code metric
file exists                         → verifier checks the filesystem
tool was used                       → inspect recorded tool-call messages
permission was respected            → inspect gate and event behavior

Qualitative claim                   → rubric-based model judge
review is grounded and useful       → judge with a specific rubric
diff is minimally invasive          → judge where a simple metric is inadequate
```

The order is important. A generic score such as “quality: 4/5” is difficult to debug, difficult to calibrate, and often detached from the failure mode we actually care about. A binary, application-specific criterion—“does the answer invent a file that does not exist?”—is far more actionable.

When a judge is necessary, it should follow the agent’s configured provider route and have a clearly versioned rubric. It should not quietly become the judge of everything. The canonical system reserves judges for the parts code cannot assess, and keeps exact behavior as exact code.

## The driver must run the real harness

An evaluation can be carefully designed and still measure the wrong thing if it uses a simplified agent loop, a separate tool dispatcher, or an observability trace as its source of truth.

`decode` drives the real agent construction, dependencies, turn handler, and runner. It extracts tool calls from the agent’s message history and usage from model response data—not from tracing exports. Traces are valuable for observability, but using them as grading truth would couple evaluation correctness to sampling, export timing, and a telemetry integration.

This is a subtle standard with broad value: use telemetry to inspect a run; use the system’s own authoritative state to grade it.

The evaluator records agent model, provider, Git revision, usage, and task results alongside the experiment. Without configuration and revision information, a pass-rate comparison says too little. A result is not reproducible merely because it has a number attached to it.

## Reliability requires repeated trials

A single successful agent run is a sample, not a reliability claim. Model outputs vary. External services vary. Tool timing and task trajectories vary. The evaluation runner therefore supports repeated trials per task and derives several complementary measures:

| Metric | Meaning |
| --- | --- |
| pass@1 | Success in one attempt. |
| pass@k | At least one success across *k* attempts. |
| pass^k | Success on every one of *k* attempts—the reliability bar. |
| Flakiness rate | How often outcomes vary across repeated trials. |
| Success per dollar | Outcome quality relative to recorded model cost. |

These metrics prevent a pleasant but misleading story. A high pass@k can mean the agent eventually succeeds if given enough retries; a lower pass^k may reveal that it is unreliable for unattended work. Cost-normalized success reminds us that an improvement that requires dramatically more requests is a product trade-off, not a free win.

The calculation is intentionally post-hoc over recorded trial results. The evaluation infrastructure should preserve the data first, then derive transparent aggregates, rather than hiding its arithmetic behind a dashboard.

## Keep costly evaluation out of ordinary CI

The production-shaped benchmark and regression tracks require a provider key and observability credentials. They run the real agent, use a sandbox, and spend money. They are therefore manual commands, not a surprise side effect of `make ci` or an ordinary unit-test run.

That is not an avoidance of quality control. It is a clear cadence:

```text
fast CI                 → deterministic unit and integration contracts
feature-branch ritual   → regression probes and threshold review
candidate comparison    → benchmark trials and reliability aggregates
live operation          → trace review and online evaluation
```

When keys are unavailable, the evaluation entry points skip with a clear, friendly message rather than failing with a traceback or silently running a mock. Skip-friendly behavior is a feature: contributors can understand what exists without accidentally incurring cost.

## Online evaluation closes the loop

Offline datasets cannot capture every way users will actually use a coding agent. Online evaluation scores traces the system has already emitted from real interactive and headless sessions.

This changes the evaluation question. Instead of recreating a task from scratch, an online rule looks at sampled real work and asks whether a criterion such as groundedness, completeness, or safe tool behavior remains acceptable.

Online evaluation should be small and deliberate. It needs trace sampling, versioned criteria, careful treatment of user and repository data, and a human review path. It is not permission to send every private session to an external judge or to automate a production decision from a single score.

The important architecture boundary is that offline experiments write to a dedicated evaluation project, while online scoring happens against the live tracing project because that is the evidence being assessed. Mixing the two would make both hard to interpret.

## Evaluation is part of shipping, not a final checkbox

The final course lesson moves from builder to operator: environment-scoped secrets, remote runtime deployment, and a pipeline in which an issue can eventually return a reviewed pull request. The evaluation stack is what makes that expansion defensible.

Before an agent is trusted with a remote sandbox, a repository branch, or a pull-request workflow, a team should be able to show:

- which benchmark tasks it reliably completes;
- which behavioral constraints it preserves;
- what its cost and failure modes look like across trials;
- where its credentials and tool authority are scoped; and
- how a human can inspect and approve the resulting change.

That last point remains non-negotiable. An agent opening a pull request is an external action with lasting consequences. Evaluation evidence can inform the decision to authorize it; it does not replace authorization.

## The larger lesson

An evaluation is not a leaderboard number, a green unit suite, or a judge saying the answer sounds good. It is a deliberately constructed chain of evidence.

```text
trusted task fixture
  + isolated execution
  + honest oracle
  + recorded configuration and usage
  + repeated trials
  + behavior-specific probes
  + human review of live evidence
  = a credible claim of improvement
```

That is where this series ends. The agent loop was always the easy part. The work was building the system around it: durable state, controlled authority, focused context, bounded parallelism, and finally an evaluation practice strong enough to tell whether the system deserves to keep evolving.

---

*This is Week 8 of my “Building a Coding Agent From Scratch” series. Explore the [canonical evaluation lesson](https://github.com/silsgah/building-a-coding-agent-from-scratch-course/tree/master/lessons/07-evals), the [evaluation guide](https://github.com/silsgah/building-a-coding-agent-from-scratch-course/blob/master/running_the_code/evals.md), and the [companion Week 8 lab](https://github.com/silsgah/coding-agent-course/tree/master/week-08-evaluation-real-world).*
