# Week 4 — Containment & Sandboxing

> Four permission modes (read-only → full trust). Docker Workspace isolation. Remote sandbox execution.

---

## Learning Objectives

By the end of this week, you will:
1. Implement **four permission modes** with graduated trust
2. Run your agent inside a **Docker container** so it can't damage your machine
3. Understand **remote sandboxing** (Modal-style) for cloud execution
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

### `remote_sandbox.py` — Remote execution concept

Demonstrates the *idea* of remote sandboxing (like Modal or E2B):
- Tool execution happens on a remote server
- Your local machine never runs untrusted code
- Multiple agents can run in parallel, each in their own sandbox

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

## Exercises

See [exercises/exercises.md](exercises/exercises.md)

## References

- [DecodingAI Lesson 5 — Permissions & Sandbox](../../building-a-coding-agent-from-scratch-course/lessons/05-permissions-and-sandbox/) — allow/ask/deny, Docker/Modal Workspace, git hand-back
- [DecodingAI sandboxing.md](../../building-a-coding-agent-from-scratch-course/running_the_code/sandboxing.md) — Docker/Modal Workspaces
- [NOOA Sandbox](../../labs-OO-Agents/examples/README.md#sandbox) — OpenShell-based isolation

---

**Deliverable:** Agent runs safely in an isolated, remote environment.
