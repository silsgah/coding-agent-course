# Building a Coding Agent From Scratch, Week 4: Permission Is Not Containment

### Asking a user before every command is useful interaction design. It is not a boundary that limits what an approved command can do.

The first three weeks of this series made a coding agent capable of acting,
resuming after interruption, and replaying a recorded decision. They also left
one uncomfortable fact exposed: the agent’s tools still run on the same machine
as the person using it.

That is tolerable for a short tutorial in a disposable folder. It is the wrong
default for an autonomous coding workflow. An approved shell command can read
more than the project, change more than one file, or use network access in ways
the model and user did not anticipate.

Week 4 separates two controls that are often conflated: **permission** decides
whether a proposed action is allowed; **containment** limits the damage an
allowed action can cause.

This is the fourth installment in my *Building a Coding Agent From Scratch*
series: the model → tool loop, durable checkpoints, replayable decision
branches, and now graduated permissions plus a Docker execution boundary.

The implementation is in the [course repository](https://github.com/silsgah/coding-agent-course/tree/master/week-04-containment-sandboxing).

## Trust is a spectrum, not a boolean

A y/n prompt for every action treats a file read and a destructive shell
command as the same risk. It also forces a user to approve repetitive,
low-risk exploration one action at a time. The Week 4 permission policy offers
four explicit modes:

| Mode | Read tools | Write tools and shell |
| --- | --- | --- |
| `deny-all` | blocked | blocked |
| `ask-all` | ask | ask |
| `auto-read` | automatic | ask |
| `full-trust` | automatic | automatic |

`auto-read` is a useful interactive default: an agent can inspect a project
without constant interruption, while a modification still requires a human
decision. `full-trust` is not a shortcut around safety. It is appropriate only
when another layer has already narrowed the agent’s authority—such as a
disposable sandbox in CI.

That ordering is the design rule: policy decides *whether* to run a tool; the
sandbox decides *where* it runs.

## Keep the agent loop outside the risky boundary

The model call, history assembly, and permission decision remain in the
harness. Only file and command execution cross into `DockerSandbox`:

```text
model proposes an action
        ↓
permission policy accepts it
        ↓
DockerSandbox executes it in /workspace
        ↓
tool result returns to the model history
```

The container is given a single mounted workspace, no network, a 512 MB memory
limit, and a 30-second command timeout. Docker removes the container after each
command. The command is passed to Docker as an argument list rather than being
interpolated into a host-side shell string:

```python
containers.run(
    "python:3.12-slim",
    command=["/bin/sh", "-lc", command],
    working_dir="/workspace",
    network_mode="none",
    mem_limit="512m",
    remove=True,
)
```

The command still runs in a container shell, but model text cannot alter the
host-shell invocation that starts the container.

## Fail closed when isolation is unavailable

The most dangerous sandbox bug is a quiet fallback: Docker fails to start, but
the agent runs the same command on the host so the demo still appears to work.

This implementation refuses host execution when Docker is unavailable. There
is an explicit `--allow-host-execution` teaching flag, but it is deliberately
noisy and must not be used for unattended or untrusted work. A sandbox that
silently degrades into host execution is not a sandbox.

File operations resolve paths before use and require the target to be the
workspace or one of its descendants. This blocks both `..` traversal and
symlink escapes through a similarly named sibling directory.

## What this lesson does—and does not—provide

The Docker implementation is a local execution boundary. It is not a remote
sandbox service, a credential broker, or a complete multi-tenant security
system. The course does not ship a Modal, E2B, or other cloud adapter. Such a
provider should implement the same narrow executor interface, with its own
identity, network, image, artifact, and cleanup policies.

Real deployments also need carefully selected mounts, minimal images, resource
limits appropriate to their workload, secret isolation, and Docker-enabled
integration tests on the target platform.

## What I tested

The four deterministic tests run without Docker or a model API. They verify
that Docker unavailability fails closed, host execution requires the explicit
override, command arguments avoid host-shell interpolation, and path checks
reject sibling-prefix and symlink escapes.

Run them from the repository root:

```bash
python -m unittest discover -s week-04-containment-sandboxing/tests -v
```

The remaining release check is intentionally separate: Docker-enabled CI should
validate that the real daemon enforces the configured network, mount, resource,
and cleanup behavior.

## The series moves from capability to authority

Weeks 1–3 asked whether the agent could act, recover, and replay. Week 4 asks
what it can touch when it acts incorrectly. The answer should never be
“whatever the developer’s laptop can touch.”

Next, I will focus on a different finite resource: context. An agent that is
allowed to act safely can still fail if every old command output and file dump
accumulates in the next model request.

---

*This is Week 4 of my “Building a Coding Agent From Scratch” series. The
project now has graduated permission modes and a Docker-backed executor that
fails closed when its isolation boundary is unavailable.*
