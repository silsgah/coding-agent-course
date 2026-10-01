# Building a Coding Agent From Scratch, Week 4: Permission Is Not Containment

### An approval decides whether an action may run. A sandbox decides what that action can reach after it runs. Treating either as a substitute for the other is how coding agents become dangerous.

In [Week 1](https://kwablagah.substack.com/p/why-the-agent-loop-is-20-lines-of?r=bpg99), I built the smallest useful coding-agent loop: model, tool call, observation, repeat. In [Week 2](https://kwablagah.substack.com/p/your-coding-agent-has-a-fatal-flaw?r=bpg99), I made the loop durable enough to survive interruption. [Week 3](https://github.com/silsgah/coding-agent-course/tree/master/week-03-replay-model-swap) turned a durable execution into an experiment: preserve the observed state, fork at a named boundary, and compare a model change honestly.

Each step made the agent more capable. This week asks the question capability makes unavoidable:

> When the model asks to run a command, what is it actually allowed to touch?

The wrong answer is: “the user clicked Allow.”

An approval is an important interaction. It tells the harness that a proposed action is permitted. It does not narrow the process’s filesystem view, remove its network, erase its inherited credentials, or stop it from following a symlink out of the project. Once an approved process runs on a developer’s machine, it has whatever authority that process has.

This is the fourth installment in my *Building a Coding Agent From Scratch* series. It follows the canonical [`decode`](https://github.com/silsgah/building-a-coding-agent-from-scratch-course) implementation and its [permissions and sandbox lesson](https://github.com/silsgah/building-a-coding-agent-from-scratch-course/tree/master/lessons/05-permissions-and-sandbox). The companion lab is still useful for learning isolated concepts; the production-shaped design lives in the shared runtime.

## Series navigation

- [Week 1 — Why the Agent Loop is 20 Lines of Code](https://kwablagah.substack.com/p/why-the-agent-loop-is-20-lines-of?r=bpg99)
- [Week 2 — Your Coding Agent Has a Fatal Flaw](https://kwablagah.substack.com/p/your-coding-agent-has-a-fatal-flaw?r=bpg99)
- [Week 3 — Replay Is an Experiment, Not a Rerun](https://github.com/silsgah/coding-agent-course/tree/master/week-03-replay-model-swap)
- **Week 4 — Permission Is Not Containment**
- Next: **Week 5 — Context Is a Budget, Not a Memory Dump**

## The approval prompt is not a security boundary

Consider a coding agent that proposes this command:

```bash
pytest -q
```

On a trusted local repository, that may be a routine request. But the command is not intrinsically harmless. Test setup can execute arbitrary code. Configuration can load plugins. A child process can inspect the environment, read files outside the repository, or make network calls. The model might have intended only to verify a patch; the operating system sees a process with the authority of the user who launched it.

The same distinction applies to a write operation. Asking before `write_file("src/app.py", ...)` makes the change visible. It does not prevent the agent from later reading `~/.ssh`, following a symlink, or invoking an approved shell command with a much broader effect.

This leads to two separate control planes:

```text
model proposes a tool call
          │
          ▼
  permission gate ─── decides: allow, ask, or deny
          │
          ▼
   execution environment ─── limits: filesystem, process, network, secrets
          │
          ▼
      tool result returns to the model
```

The permission gate governs *intent*. The execution environment governs *blast radius*. Good agent systems need both.

## Make the permission layer deterministic

Permissions should not be another model prompt. The model is the untrusted party proposing the action; it should not be the component that decides whether its own request is safe.

In `decode`, a permission request carries the tool name, arguments, tool category, and subject. A deterministic gate then produces one of three outcomes: allow, ask, or deny. The normal interactive posture is deliberately practical: read-only exploration can proceed without interrupting every turn, while writes and shell commands surface for approval. Rules in `.decode/settings.json` can allow a narrow, explicit class of calls—such as a particular Git command—without converting all shell access into ambient trust.

That produces a trust ladder rather than a single all-or-nothing toggle:

| Request | Sensible default | Why |
| --- | --- | --- |
| Read a source file | allow | Exploration needs feedback; the operation is bounded by the tool scope. |
| Write or edit a source file | ask | A human should see proposed mutation before it occurs. |
| Run `bash` | ask | The command may execute arbitrary programs and create child processes. |
| Explicitly matched rule | allow | The rule is a reviewed policy decision, not a model inference. |
| Explicitly denied rule | deny | The agent receives a refusal and must adapt. |

The important property is explainability. When an action is automatically allowed, we should be able to point to the policy that did it. When it is denied, the model gets a clear observation rather than a mysterious failure. And when a human approves an action, the approval applies to the request we showed them—not to every future command the agent might invent.

Permission decisions are necessary, but they are deliberately not enough.

## The sandbox has to contain the whole tool scope

The first sandbox design many people build is incomplete: send `bash` to a container but let `read`, `write`, and `edit` continue to operate on the real host checkout. This seems safer because commands are isolated. In practice, the agent still has host file authority through a second tool set, and its tools no longer agree about what files exist.

The canonical implementation fixes this by moving the whole agent tool scope into an isolated Workspace when sandbox mode is selected. Shell commands, file reads, edits, directory searches, and globbing operate against the same workspace. The agent is not reading one filesystem and writing another.

There is a clean separation of responsibilities:

```text
Harness Home (host)                         Isolated Workspace (agent tool scope)

.decode/settings.json                      cloned repository or empty workspace
.decode/sessions                            read / write / edit / glob / grep
.decode/MEMORY.md                           bash
skills, logs, runtime state                 model-created files and dependencies
```

The harness keeps its own records and policy configuration at the launch directory. The agent’s code-facing tools are redirected into the Workspace. This is more than tidiness: it prevents a model task from casually reaching session logs, settings, or unrelated project files simply because they sit beside the repository.

For a sandboxed repository task, the operator supplies the source repository explicitly. The harness creates a workspace from the source’s committed HEAD, and the agent works there:

```bash
SANDBOX_MODE=docker uv run decode run \
  --repo https://github.com/<you>/<repo> \
  "Find the failing test, make the smallest correct fix, and run it"
```

This is an important operational detail: a headless run treats a failed clone as fatal. An unattended agent silently working in an empty directory after a malformed repository URL is not a recoverable convenience; it is wasted execution and misleading output.

## One executor seam, two isolation rungs

The agent loop should not need a different implementation for each sandbox provider. `decode` keeps a narrow executor seam: the loop asks an executor to run a command and perform workspace I/O; the selected backend provides the environment.

The two shipped sandbox modes have distinct threat models:

| Mode | Where code runs | Honest use case |
| --- | --- | --- |
| `none` | Host process | Trusted local development; no containment. |
| `docker` | Local container Workspace | Reducing accidental damage on a developer machine. |
| `modal` | Remote disposable Workspace | Work that should not execute on the developer’s machine. |

Docker is a valuable teaching and local-development boundary, but it is not magic. On Linux it shares the host kernel; on macOS and Windows, Docker Desktop adds a VM boundary. It is appropriate for reducing accidental misbehavior, not for claiming that hostile code is harmless. The remote Modal option is the higher isolation rung: the tool process runs away from the laptop entirely.

Both backends satisfy the same workspace contract. The agent sees `/workspace`; each command is a fresh execution in the same session workspace, so filesystem changes persist while shell-local state such as `cd` or exported environment variables is not silently relied on across calls. This is a useful constraint. It makes each command’s behavior easier to describe, time out, and replay.

## File tools need their own containment rules

Putting a workspace in a container does not eliminate path bugs. A tool that accepts `../outside.txt`, an absolute path, or a symlink that resolves beyond the mounted workspace can still escape its intended scope.

The implementation therefore layers containment:

1. Backend-independent logical path validation rejects absolute paths and parent-directory escapes.
2. The Docker backend resolves paths physically as well, so a symlink planted inside the workspace cannot lead a host-backed mount to an unrelated host path.
3. Remote file operations use the remote workspace API directly; they are not maintained as an unreliable host mirror.

This distinction between logical and physical containment is easy to skip in a prototype. String checks catch `../secrets`; they do not catch a file named `linked-config` that points somewhere else. A safe tool surface must define both the paths the agent may name and the final locations those paths resolve to.

## What stays outside the sandbox

“Sandboxed agent” is not a universal statement. It must be tool-specific.

The model loop, permission gate, durable runtime, and harness artifacts remain host-side. Structured file operations keep their high-level validation in the harness, even when their bytes travel through a sandbox backend. `web_fetch` also remains a host-side, permission-gated network operation. A task that says “fetch this URL” is therefore not automatically contained by the Docker or Modal workspace.

That is not a contradiction; it is an explicit placement decision. The alternative—pretending every tool is in the same boundary—is worse. A reliable system names where each class of work happens and applies its policy accordingly.

## Shipping results without giving the agent your credentials

An isolated workspace creates a practical problem: the agent may make a correct change, but the operator still needs that change to return to the repository.

The default answer is **hand-back**. At the end of a sandbox session, the harness collects the workspace state, preserves any model commits, commits uncommitted work when necessary, creates a deterministic `decode/<session-id>` branch, and pushes it using the host’s ambient Git credentials. If the push fails, the local session branch and workspace are retained for inspection rather than discarded.

This means the default workflow can return an agent’s work without copying a GitHub token into the sandbox. It is a narrower authority design: the agent can modify its disposable workspace, while the trusted harness performs the final transport.

There is an intentional opt-in for the larger authority: `SANDBOX_GIT_TOKEN` lets the sandboxed agent itself run `git push` or open a pull request. That token is injected as `GITHUB_TOKEN` and is readable by a process in the workspace. The correct mitigation is not wishful language about containers; it is a fine-grained, repository-scoped, revocable token—or, preferably, leaving the option unset and using hand-back.

## Test the security claims, not just the happy path

Security architecture is only credible when its negative paths are testable. The canonical project includes a sandbox capstone and real Docker integration coverage. The meaningful claims include:

- a denied tool request never reaches the executor;
- sandbox selection changes the executor without changing the agent loop;
- file tools and shell commands observe one truthful workspace;
- an attempted logical or symlink workspace escape becomes a refusal;
- a missing Docker daemon or missing remote credentials fails loudly before an agent run starts;
- a failed headless repository clone stops the run rather than creating an empty-workspace success story; and
- work survives a failed hand-back as a retained session branch or workspace artifact.

These tests do not prove that no sandbox can ever be bypassed. They prove the boundaries the application claims to enforce. That is the right standard: precise, testable, and honest about what remains outside the boundary.

## The larger lesson

Week 4 is not about adding another warning dialog to an agent. It is about separating authority into layers.

The permission layer answers, “May this request proceed?” The workspace answers, “What can this approved request affect?” Credential handling answers, “What secret, if any, does the process actually receive?” Hand-back answers, “How does useful work leave the isolated environment without widening the agent’s authority?”

Once those questions are explicit, the system becomes much easier to reason about—and much harder to accidentally over-trust.

Next week, I will turn from authority to another limit agents routinely ignore: context. A coding agent can be perfectly sandboxed and still fail if it keeps feeding every stale command output, file dump, and earlier decision back into the next model call.

---

*This is Week 4 of my “Building a Coding Agent From Scratch” series. For the runnable implementation, see the [canonical permissions and sandbox lesson](https://github.com/silsgah/building-a-coding-agent-from-scratch-course/tree/master/lessons/05-permissions-and-sandbox) and the [companion Week 4 lab](https://github.com/silsgah/coding-agent-course/tree/master/week-04-containment-sandboxing).*
