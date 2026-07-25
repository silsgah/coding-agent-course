# Week 4 — Exercises

## Exercise 1: Try all four permission modes
Run `permission_modes.py` with each mode and the same task ("list files and create a summary"). Compare:
- How many approval prompts did you get?
- Which mode felt most productive? Most safe?

## Exercise 2: Path escape attack
Try to trick the agent into reading files outside the workspace (e.g., `../../.ssh/id_rsa`). Does the sandbox catch it? Add a path validation check if it doesn't.

## Exercise 3: Network isolation test
Ask the agent to `curl https://google.com` inside the Docker sandbox. Does it fail? Add a `--network` flag to optionally allow network access for tasks that need it (like `pip install`).

## Exercise 4: Custom Docker image
Create a Dockerfile with your project's dependencies pre-installed. Modify `docker_workspace.py` to use your custom image instead of `python:3.12-slim`.

## Exercise 5: Permission mode persistence
Save the chosen permission mode to a `.agent-config.json` file so it persists between sessions. Add a `/mode` command to switch modes interactively.
