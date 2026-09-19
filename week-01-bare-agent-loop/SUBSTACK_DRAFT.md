# Building a Coding Agent From Scratch, Week 1: The Loop Is Small. The Harness Is the Product.

### A coding agent is not a chatbot with a terminal. It is a control loop that decides when a model may observe, propose an action, and receive the result.

The first version of a coding agent can be disarmingly short. Give a model a
user request, offer a few tools, execute the tool it selects, return the
observation, and repeat until it answers.

That small loop is worth building from scratch because it reveals where the
real engineering begins. A model does not read a repository by itself. It does
not run a test suite by itself. It cannot tell whether a command was approved,
whether a path was safe, whether a previous action succeeded, or how much of a
long investigation should remain in context. The harness makes those choices.

This is the first installment in my *Building a Coding Agent From Scratch*
series. Week 1 establishes the smallest useful contract:

```text
user request → model → proposed tool call → human approval → tool result → model
```

The point is not to claim that this is a production runtime. It is the
opposite: to make the missing production concerns visible before a framework
hides them.

The complete Week 1 implementation is in the
[course repository](https://github.com/silsgah/coding-agent-course/tree/master/week-01-bare-agent-loop).

## A concrete turn: “Read the README and tell me how to run the project”

Suppose a user asks an agent to inspect a repository’s README. The agent needs
more than a fluent answer; it needs evidence from the file. The harness sends
the system instruction, the conversation so far, and tool schemas to the
model. The model may return a request like this:

```json
{
  "name": "read_file",
  "arguments": {"path": "README.md"}
}
```

The crucial word is *may*. A tool call is a proposal from the model, not an
instruction the runtime must obey. Before executing it, this first version
stops at a human permission gate. If the user approves, the harness reads the
file. If the user denies it, the denial becomes an observation in the same
conversation. The model can then explain that it could not inspect the file or
choose a different path.

That distinction prevents a subtle failure mode: an agent should not quietly
end a turn because an action was refused. A refusal is part of the task state.

## The agent loop in one place

The core implementation is an asynchronous loop with a deliberately bounded
iteration count:

```python
for iteration in range(max_iterations):
    messages = [Message(role="system", content=SYSTEM_PROMPT)] + history
    response = await provider.chat(messages, tools=TOOL_SCHEMAS)

    if response.tool_calls:
        for tool_call in response.tool_calls:
            approved = permission_resolver(
                tool_call.name, tool_call.arguments
            )
            result = (
                tool_executor(tool_call.name, tool_call.arguments)
                if approved
                else "⛔ User denied this tool call."
            )
            history.append(Message(
                role="assistant", content="",
                tool_calls=[{
                    "id": tool_call.id,
                    "name": tool_call.name,
                    "arguments": tool_call.arguments,
                }],
                raw_parts=response.raw_parts,
            ))
            history.append(Message(
                role="tool", content=result, tool_call_id=tool_call.id
            ))
        continue

    if response.content:
        history.append(Message(role="assistant", content=response.content))
        return response.content
```

The loop has only two terminal states: a final text answer from the model or a
maximum-iteration limit. Everything else is an observation cycle. That is the
basic ReAct shape—reason, act, observe, repeat—but the interesting details are
in the data contract around it.

The assistant tool-call message is stored before the corresponding tool result,
and the result carries the same call identifier. Tool-aware model APIs use that
pairing to reconstruct what happened: the assistant requested one operation;
the environment returned this specific result. Dropping either half produces a
conversation the next model call cannot interpret reliably.

## Why the permission gate belongs in the harness

Week 1 offers three intentionally simple tools:

- `read_file`
- `write_file`
- `bash`

The model can choose among them, but it does not grant itself authority. The
permission resolver sits between selection and execution for every call. That
is a small mechanism, but it establishes a design rule that remains useful as
the course grows: the model proposes; the harness enforces policy.

For an interactive lesson, a y/n prompt makes the policy visible. It is not a
complete security boundary. The tools in this first module still operate on the
host machine, and `bash` is unrestricted after approval. It should therefore
be run only in a disposable or intentionally scoped workspace. Later modules
will add permission modes, workspace boundaries, and sandboxed execution.

Being explicit about this limit matters more than decorating the demo with a
"secure" label. A visible approval prompt is useful human control; it is not
isolation.

## Make the loop testable without calling a model

Agent demos often require an API key before they can be verified. That makes it
easy to test the model connection and hard to test the harness behavior. The
Week 1 loop now accepts three injected seams:

```python
async def agent_loop(
    user_message,
    history,
    *,
    provider_factory=get_provider,
    permission_resolver=ask_permission,
    tool_executor=execute_tool,
):
    ...
```

The default interactive behavior is unchanged. In an offline test, however, a
scripted provider can request a tool call and then return a final answer; a
test-owned executor can return a known string; and the permission resolver can
approve or deny deterministically.

The two tests verify the harness contracts that matter at this stage:

1. An approved tool’s result is added to history and is visible to the next
   model call.
2. A denied tool does not execute, but the model still receives an explicit
   denial observation and can finish the turn coherently.

Run them from the repository root:

```bash
python -m unittest discover -s week-01-bare-agent-loop/tests -v
```

These are not intelligence benchmarks. They do not prove a model can repair a
bug or understand an unfamiliar codebase. They prove that the control loop
preserves the information a model needs after a tool decision, without a live
provider call.

## What Week 1 deliberately does not solve

The bare loop has no durable state. A crash loses the conversation and any
knowledge of completed work. It has no replay boundary for comparing one
decision against another. It does not manage context growth, and it does not
offer a safe sandbox for command execution.

Those are not reasons to skip the loop. They are the reasons to start here.
Once the loop is explicit, each later capability has a precise place to attach:
durable events around the tool cycle, replay over a recorded history, policy
between proposal and execution, and context controls before the next model
request.

The lesson I am carrying forward is simple: model quality matters, but an
agent’s behavior is shaped just as much by what its runtime records, permits,
returns, and refuses to do.

Next week, I will make this loop survive interruption. The durable runtime will
write an append-only event log around the same model → tool → observation cycle,
so a restarted agent can continue from evidence it already paid to collect.

---

*This is Week 1 of my “Building a Coding Agent From Scratch” series. The
implementation is a minimal, human-approved tool loop with deterministic
offline tests for its history and permission contracts.*
