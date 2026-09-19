# Week 4 — Containment & Sandboxing

> Four permission modes (read-only → full trust) and Docker workspace isolation.

---

## Learning Objectives

By the end of this week, you will:
1. Implement **four permission modes** with graduated trust
2. Run your agent inside a **Docker container** so it can't damage your machine
3. Understand where a remote sandbox adapter would fit in the execution boundary
4. Know why containment is a **harness problem**, not a model problem

## The Big Idea

Your Week 1 agent has a y/n gate on every tool call. That's usable for demos, but it breaks down in practice:

- **Too slow**: A 50-step task means 50 approvals
- **Too binary**: Reading a file is not the same risk as `rm -rf /`
- **No isolation**: Even approved commands run on *your* machine

Real coding agents solve this with **graduated trust** and **isolation**:

1. **Permission modes** — different levels of autonomy
2. **Sandboxing** — execute in a disposable environment

These are the two mechanisms that let an agent be both *useful* (autonomous enough to work) and *safe* (contained enough to trust).

## Permission Modes

| Mode | Read tools | Write tools | Bash | Use case |
|---|---|---|---|---|
| `deny-all` | ❌ Blocked | ❌ Blocked | ❌ Blocked | Review mode — model can only talk |
| `ask-all` | ✅ Ask | ✅ Ask | ✅ Ask | Week 1 behavior — human approves everything |
| `auto-read` | ✅ Auto | ✅ Ask | ✅ Ask | Normal use — reads are safe, writes need approval |
| `full-trust` | ✅ Auto | ✅ Auto | ✅ Auto | Headless / CI — everything auto-approved (use with sandbox!) |

The key insight: `full-trust` mode is *only safe inside a sandbox*. The two features are designed to work together.

## Sandbox Architecture

```
    Your Machine                    Docker Container
    ┌──────────────┐                ┌──────────────┐
    │  Agent Loop  │ ──commands──▶  │  bash, file  │
    │  (harness)   │                │  operations   │
    │              │ ◀──results───  │              │
    │  Permission  │                │  Disposable! │
    │  Gate        │                │  No secrets  │
    └──────────────┘                └──────────────┘

    The agent loop stays on your machine.
    Only tool execution happens in the container.
```

## Code Walkthrough

### `permission_modes.py` — Four levels of trust

Replaces the Week 1 permission gate with a mode-aware system. Each mode defines:
- Which tool categories auto-approve
- Which require human approval
- Which are blocked entirely

### `docker_workspace.py` — Docker isolation

Wraps tool execution in a Docker container:
- Mount only the project directory (read-only or read-write)
- No network access by default
- No access to your SSH keys, env vars, or other repos
- Container is destroyed after the session

### Remote execution — extension point

This lesson implements Docker locally. A remote sandbox provider (for example,
one that creates short-lived cloud workspaces) belongs behind the same tool
execution boundary, but is intentionally not included as a runnable adapter.

## Key Design Decisions

### Why separate the agent loop from tool execution?
Because the agent loop (prompt assembly, model calls, history) doesn't need isolation — it's deterministic harness code. Only tool execution (bash, file writes) is dangerous. Separating them lets you sandbox just the dangerous part.

### Why four modes instead of two?
Because the spectrum of trust isn't binary. `auto-read` is the sweet spot for most interactive use: the agent can explore the codebase freely but can't modify anything without your approval.

### Why Docker and not just a chroot?
Docker provides filesystem, network, and process isolation. A chroot only isolates the filesystem. When the agent runs `curl` or `pip install`, you want network isolation too.

---

## Run It

```bash
cd week-04-containment-sandboxing/code

# Try different permission modes
python permission_modes.py --mode auto-read
python permission_modes.py --mode full-trust

# Run with Docker isolation (requires Docker)
python docker_workspace.py
```

Docker command execution **fails closed** when Docker is unavailable. The
teaching-only `--allow-host-execution` flag is an explicit opt-in and must not
be used for unattended or untrusted work.

## Test It

```bash
python -m unittest discover -s week-04-containment-sandboxing/tests -v
```

## Exercises

See [exercises/exercises.md](exercises/exercises.md)

## References

- [DecodingAI Lesson 5 — Permissions & Sandbox](../../building-a-coding-agent-from-scratch-course/lessons/05-permissions-and-sandbox/) — allow/ask/deny, Docker/Modal Workspace, git hand-back
- [DecodingAI sandboxing.md](../../building-a-coding-agent-from-scratch-course/running_the_code/sandboxing.md) — Docker/Modal Workspaces
- [NOOA Sandbox](../../labs-OO-Agents/examples/README.md#sandbox) — OpenShell-based isolation

---

**Deliverable:** An agent execution boundary with graduated permissions and a
Docker-backed local sandbox that fails closed when Docker is unavailable.
