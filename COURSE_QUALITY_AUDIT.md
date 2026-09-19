# Course Quality Audit

**Audit date:** 2026-09-19  
**Scope:** Weeks 1–8 lesson READMEs, runnable Python, test coverage, Substack drafts, and release claims.  
**Standard:** A lesson claim must map to committed code, an executable command, a bounded safety model, and a repeatable verification path.

## Executive Summary

The course has a clear learning progression and the strongest recent modules
(Weeks 3–8) now have deterministic tests and honest operational boundaries.
It is **not yet safe to describe the whole course as production-grade**. The
original P0 code-safety issues are remediated; the remaining release work is
integration coverage, baseline tests, and article completion.

## Evidence Collected

- All Python files under `week-*/code/` compile with `py_compile`.
- Existing offline suites pass: Week 3 (6 tests), Week 4 (4), Week 5 (6), Week
  6 (6), Week 7 (6), and Week 8 (5): **33 tests total**.
- Weeks 1 and 2 currently have no dedicated automated test directory.
- Substack drafts exist for Weeks 3, 5, and 7 only.
- Week 8 includes a safe local issue review-packet command and a non-overwriting
  capstone template; neither makes external GitHub writes.

## Release Gates

| Gate | Requirement | Current status | Required action |
| --- | --- | --- | --- |
| Safety | No silent host execution when sandbox setup fails | Code fixed | Week 4 now fails closed; run a real Docker integration check in CI. |
| Isolation | Workspace paths are robust against sibling-prefix and symlink escapes | Code fixed | Week 4 now uses resolved-path ancestry checks; retain regression tests. |
| Evaluation safety | No executable validator strings | Code fixed | Week 8 uses trusted validator callables; retain regression tests. |
| Eval isolation | Every benchmark uses a scoped executor/workspace | Code fixed | Week 8 uses a workspace executor and does not change process CWD. |
| Testability | Every week has offline deterministic checks | Partial | Add dedicated tests for Weeks 1 and 2. |
| Documentation | Every advertised command exists and is runnable | Code fixed | Week 8 now provides safe local review-packet and template commands. |
| Publishing | Each post matches code, evidence, and series structure | Partial | Add drafts for Weeks 1, 2, 4, 6, and 8; then run the article checklist below. |

## Findings by Week

### Week 1 — Bare Agent Loop

**Strength:** It teaches the essential ReAct sequence and puts a human approval
gate in the loop.

**Gap:** Tools operate directly on the host and there are no tests for tool
argument handling, approval denial, or history pairing. Keep the lesson as a
minimal baseline, but label it as intentionally unsafe outside a disposable
workspace.

### Week 2 — Resumability and Checkpoints

**Strength:** Append-only event history is the correct durable artifact; the
current dangling-tool-call recovery logic addresses a real provider contract.

**Gap:** No committed tests currently cover checkpoint round-trips, interrupted
tool calls, malformed JSONL, or exactly-once resume semantics.

### Week 3 — Replay and Model Swap

**Strength:** Source sessions remain immutable, branches record replay
metadata, metrics are persisted, and six offline tests exercise the core
replay contract.

**Gap:** A live replay should ultimately execute through the sandbox seam, not
directly through host tools. Cost figures must remain explicitly approximate.

### Week 4 — Containment and Sandboxing

**Remediated in Week 4 hardening:** Docker unavailability now fails closed;
host execution requires the explicit `--allow-host-execution` teaching flag.
Docker receives its command as an argument array rather than host-side quoted
interpolation, and file tools use resolved-path ancestry checks. Four offline
tests cover those contracts.

**Remaining check:** Add a Docker-enabled integration job to confirm container
limits, network isolation, and cleanup on the supported CI runner.

### Week 5 — Context Budget

**Strength:** The module distinguishes memory, skills, compaction, and focused
symbol context. It uses disposable demo state and has six deterministic tests.

**Gap:** Token estimates are educational approximations, not provider token
accounting; the README and article correctly state this boundary.

### Week 6 — Agent as Object

**Strength:** Method discovery, schema derivation, dependency injection,
workspace-scoped file tools, safe output limits, and six offline tests make
this one of the most maintainable modules.

**Gap:** Its local command policy is defense in depth, not sandboxing. Keep the
current documentation wording and avoid presenting the blocklist as isolation.

### Week 7 — Parallel Subagents

**Strength:** Fan-out is capped, reports are structured, time/token/turn
budgets are explicit, retries are controlled, and default tools are read-only
and workspace scoped. Six offline tests cover those contracts.

**Gap:** Add an aggregate swarm budget and sandboxed executor integration
before enabling write-capable children or unattended runs.

### Week 8 — Evaluation and Capstone

**Remediated in Week 8 hardening:** Validators are trusted callables, never
runtime-evaluated strings. Each task uses a scoped workspace executor and the
runner does not mutate process CWD. Results can be written as JSON. Five offline
tests cover those safety and fixture contracts.

**Documentation gap resolved:** The advertised issue and capstone commands now
generate a local review packet and non-overwriting capstone template. They make
no GitHub writes; an authorized integration and human review remain required to
open a PR.

**Remaining work:** Add regression thresholds and a sandbox-backed integration
run before treating benchmark results as a release gate.

## Article Standard

Before publishing an installment, verify all of the following:

1. **Hook:** starts with a real operational problem, not a generic definition.
2. **Continuity:** names the prior capability it builds on and the next one it
   enables.
3. **System trace:** follows one concrete task through the components that
   matter.
4. **Code evidence:** every code block is current, minimal, and linked to a
   committed file.
5. **Measurement:** labels offline estimates, smoke tests, and live benchmark
   results correctly; never treats one as another.
6. **Failure boundary:** identifies what can fail, what authority the agent has,
   and what the harness does in response.
7. **Reader action:** ends with a reproducible command and expected artifact.
8. **Claims:** avoids unsupported benchmark, cost, security, or production
   claims; citations support factual external claims.

## Remediation Order

1. **Weeks 1–2 tests** — establish the baseline contracts that later lessons
   depend on.
2. **Integration coverage** — add Docker-enabled Week 4 and sandbox-backed
   Week 8 runs, then define regression thresholds.
3. **Article completion** — create/review all missing drafts against the
   article standard.
4. **Consolidation** — extract shared runtime, executor, reporting, and test
   fixtures into one package only after the lesson examples are proven.

## Definition of Done for the Course

The course is ready for a professional public release when every advertised
command exists, all lesson code has a deterministic offline test path, live
examples are opt-in and sandboxed, the evaluation suite is free of runtime
code execution, and each Substack article is backed by a reproducible run and
an honest statement of its limits.
