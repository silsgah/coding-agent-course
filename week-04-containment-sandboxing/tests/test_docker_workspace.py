"""Offline safety tests for the Week 4 Docker executor."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parents[1] / "code"
sys.path.insert(0, str(CODE_DIR))

from docker_workspace import DockerSandbox


class FakeContainers:
    def __init__(self) -> None:
        self.arguments = None

    def run(self, *args, **kwargs):
        self.arguments = (args, kwargs)
        return b"sandbox output\n"


class FakeDockerClient:
    def __init__(self) -> None:
        self.containers = FakeContainers()

    def ping(self) -> None:
        return None


class DockerSandboxTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temporary_directory.name) / "workspace"
        self.workspace.mkdir()
        (self.workspace / "inside.txt").write_text("inside", encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_unavailable_docker_fails_closed_by_default(self) -> None:
        sandbox = DockerSandbox(self.workspace, docker_client=object())
        self.assertFalse(sandbox.is_available)
        self.assertIn("refusing host command execution", sandbox.execute_bash("echo should-not-run"))

    def test_host_fallback_requires_explicit_opt_in(self) -> None:
        sandbox = DockerSandbox(self.workspace, docker_client=object(), allow_host_execution=True)
        sandbox._local_bash = lambda command: f"host override: {command}"  # type: ignore[method-assign]
        self.assertEqual(sandbox.execute_bash("echo permitted"), "host override: echo permitted")

    def test_docker_command_is_passed_as_arguments_not_interpolated_host_shell(self) -> None:
        client = FakeDockerClient()
        sandbox = DockerSandbox(self.workspace, docker_client=client)
        self.assertEqual(sandbox.execute_bash("echo 'quoted'"), "sandbox output\n")
        _, kwargs = client.containers.arguments
        self.assertEqual(kwargs["command"], ["/bin/sh", "-lc", "echo 'quoted'"])
        self.assertEqual(kwargs["network_mode"], "none")

    def test_paths_must_be_descendants_not_string_prefixes(self) -> None:
        sibling = self.workspace.parent / f"{self.workspace.name}-other"
        sibling.mkdir()
        (sibling / "secret.txt").write_text("secret", encoding="utf-8")
        sandbox = DockerSandbox(self.workspace, docker_client=object())
        self.assertEqual(sandbox.execute_read_file("inside.txt"), "inside")
        self.assertIn("Path escapes workspace", sandbox.execute_read_file("../" + sibling.name + "/secret.txt"))
        self.assertIn("Path escapes workspace", sandbox.execute_write_file("../" + sibling.name + "/new.txt", "no"))


if __name__ == "__main__":
    unittest.main()
