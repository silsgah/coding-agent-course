# Reference Alignment Plan

**Date:** 2026-09-30
**Reference implementation:** [`silsgah/building-a-coding-agent-from-scratch-course`](../building-a-coding-agent-from-scratch-course/)
**Companion course:** this repository (`coding-agent-course`)

## Decision

The reference implementation is the canonical runnable coding agent. This
repository should become its **teaching and publishing companion**, not claim
to be an equivalent production-grade implementation through eight disconnected
week directories.

The existing Week 1–2 Substack publications remain useful introductions. Drafts
for Weeks 3–8 must be revised before publication so they describe the
integrated `decode` application and its verified operator surface rather than
the smaller illustrative scripts in this repository.

## Evidence

| Dimension | Reference implementation | Current companion |
| --- | ---: | ---: |
| Python modules | 76 | 38 |
| Test files | 119 | 8 |
| Architecture decision records | 19 | 0 |
| Runnable surface | `decode` CLI/TUI, headless runtime, Docker/Modal modes | separate weekly scripts |
| Integration coverage | sandbox, runtime, observability, LSP, subagents, evals | offline unit-style lesson checks |
| Operational docs | setup, credentials, runtime, sandboxing, evals, infrastructure | per-week READMEs |

The counts are directional evidence, not a quality score. The important
difference is architectural: the reference system has one shared runtime and
one execution seam; the companion examples do not compose into the same agent.

## What changes

1. **Canonical code links**
   - Each lesson and Substack installment links first to the corresponding
     `decode` lesson, operator command, and source package.
   - The illustrative scripts remain as minimal learning artifacts, clearly
     labelled as such.

2. **Series map follows the real implementation**
   - System design
   - Agent loop and human control
   - Durable runtime and replay
   - Context engineering
   - Permissions and sandboxing
   - Subagents and fan-out
   - Evals and regression probes
   - Shipping and remote operation

3. **Publishing standard changes**
   - Week 3–8 Substack drafts are source material, not publication-ready
     installments.
   - A revised article must cite a reproducible `decode` command, the matching
     lesson, an ADR where a non-obvious decision is made, and the relevant test
     or integration proof.
   - Do not use unsupported claims such as “production-grade”, “remote swarm”,
     or “LLM-as-judge” unless the post names the exact implementation and its
     operational boundary.

4. **Companion quality gates**
   - Add a root-level development interface (`Makefile`/documented commands).
   - Add an ADR index for decisions unique to the companion course.
   - Replace aggregate test counts with separate unit and integration evidence.
   - Add a CI workflow that executes the companion's deterministic tests and
     link checks.

## Recommended order

1. Rework the root README and course map around the canonical `decode`
   implementation.
2. Rewrite Week 3 as the first corrected article: durable runtime → replay,
   using the reference runtime lesson and replay command.
3. Rework Weeks 4–8 in reference lesson order; do not publish the current
   Substack drafts before that review.
4. Add companion CI and ADRs for its own editorial and educational decisions.
5. Optionally retain the small scripts as a separate “from-scratch labs” track.

## Explicit non-goal

Do not copy the reference implementation wholesale into this repository. That
would create two diverging products. The course should explain and point to the
canonical system, while its small examples stay focused on one concept at a
time.
