# Building a Coding Agent From Scratch, Week 8: An Evaluation Is Evidence, Not a Vibe

### A green unit suite says the harness did what its components promised. It does not yet say an agent completed a representative coding task correctly.

After seven weeks, this series has a tool loop, durable checkpoints, replay,
sandbox boundaries, context controls, an inspectable harness, and bounded
subagents. The natural temptation is to call that a finished coding agent.

It is not finished until there is a repeatable way to ask whether changes make
the agent better, worse, or merely different.

Week 8 adds the first evaluation layer: isolated fixture tasks, trusted
validators, bounded agent runs, JSON results, and a local issue-to-review
packet. It deliberately stops short of live GitHub writes, automated pull
requests, and an LLM judge. Those require a separate authorized integration and
calibration process.

This is the final installment in my *Building a Coding Agent From Scratch*
series. The implementation is in the [course repository](https://github.com/silsgah/coding-agent-course/tree/master/week-08-evaluation-real-world).

## A benchmark needs a controlled world

The suite defines tasks such as creating `hello.py`, listing files, extracting
numbers from a fixture, writing output files, and reporting a missing file.
Each task starts in its own temporary workspace.

That isolation is not just tidiness. If two benchmark cases share a directory,
a file left behind by one case can make another pass for the wrong reason. The
runner never changes the process working directory; it gives each task a scoped
executor instead:

```python
with tempfile.TemporaryDirectory(prefix=f"bench-{task.name}-") as directory:
    workspace = Path(directory)
    result = await run_benchmark_task(task, workspace, provider_factory)
```

The executor exposes only `read_file`, `write_file`, and `list_files`, resolving
every path against that task’s workspace. A benchmark should measure the
capability it claims to measure—not accidental access to the repository where
the suite happens to run.

## Validators are harness code, never model-provided programs

A benchmark needs a clear pass condition. It is tempting to store a condition
as a string and evaluate it dynamically. That turns test data into executable
code, which is exactly the kind of blurred authority boundary an agent harness
is supposed to avoid.

Week 8 makes validators trusted Python callables selected by the harness:

```python
@dataclass(frozen=True)
class BenchmarkTask:
    name: str
    prompt: str
    validator: Callable[[Path, str], bool]
```

The file-creation validator, for example, checks whether `hello.py` exists and
contains a `greet` function. The model may write files and answer the task, but
it never supplies code that the benchmark runner executes to decide its score.

Evaluation rules are part of the trusted computing base. They deserve code
review, tests, and stable versioning just like the agent runtime.

## Budgets turn a run into a measurement

Each task has token and iteration limits. The suite records whether it passed,
its score, tokens, tool calls, elapsed time, final answer, and any error. It
can also write the result set as JSON:

```bash
python code/benchmark_suite.py --json-out benchmark-results.json
```

Those fields are evidence, not a quality verdict. Fewer tool calls may mean a
more efficient solution—or a skipped investigation. A perfect fixture pass rate
on five course tasks does not establish performance on a real repository.
Regression thresholds should follow a measured baseline on representative work.

## From an issue to a review packet, not an unattended pull request

The capstone command accepts local issue text and writes a JSON review packet.
It records a staged authority plan:

```text
explore   → read-only sandbox
implement → write-enabled sandbox
verify    → sandboxed test runner
review    → human decision
```

It also lists the evidence required before a change can move forward: sandbox
identifier, changed files, test output, benchmark results, and human approval.
The command makes no GitHub API call, creates no branch, and opens no pull
request.

That restraint is intentional. An issue title is not authorization to modify a
repository, and a passing local benchmark is not permission to publish code.
A real integration should use narrowly scoped credentials, a sandbox per run,
an auditable change handoff, and explicit human approval before external writes.

## What I tested

The five offline tests verify that every task requires a callable validator,
fixtures receive isolated workspaces while the runner preserves process CWD,
executor paths cannot escape their benchmark workspace, the tool loop produces
JSON-serializable results, and the issue planner produces a no-external-effects
packet that requires human review.

Run them from the repository root:

```bash
python -m unittest discover -s week-08-evaluation-real-world/tests -v
```

## What remains after the capstone

The course ends with an intentionally unfinished production checklist: Docker-
backed integration tests, regression baselines and thresholds, representative
real-repository tasks, and a calibrated online judge only if human evaluation
confirms it is reliable enough for the chosen decision.

The broader lesson is that an agent is not ready because it can make a change.
It is ready when a team can reproduce the conditions of that change, inspect
its authority and evidence, and detect when the next version regresses.

---

*This is Week 8 of my “Building a Coding Agent From Scratch” series. The
project now has isolated benchmark fixtures, trusted validators, bounded runs,
machine-readable results, and a local human-review handoff.*
