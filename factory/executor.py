"""Explicit local Docker adapter. No host-shell fallback or automatic image pull."""
from __future__ import annotations

import os
from pathlib import Path
import re
import selectors
import shutil
import signal
import subprocess
import tempfile
import time
import uuid

from .config import FactoryConfig
from .storage import ProjectStore, StorageError, tree_hash, safe_path
from .utils import utc_now, sha256_text, stable_json

TOOL_COMMANDS = {"python.unittest": ("python", "-I", "-B", "-m", "unittest", "discover", "-s", "/workspace/tests", "-v")}


def redact(text: str) -> str:
    text = re.sub(r"-----BEGIN [^-]*PRIVATE KEY-----[\s\S]*?(?:-----END [^-]*PRIVATE KEY-----|$)", "[REDACTED KEY]", text)
    text = re.sub(r"(?i)(authorization[\"\']?\s*:\s*[\"\']?bearer\s+|(?:password|api[_-]?key|secret|access[_-]?token)[\"\']?\s*[=:]\s*)[^\s,;]+", r"\1[REDACTED]", text)
    return re.sub(r"\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{16,}|glpat-[A-Za-z0-9_-]{16,})\b", "[REDACTED]", text)


class ToolExecutor:
    def __init__(self, store: ProjectStore, config: FactoryConfig) -> None:
        self.store, self.config = store, config
        self.policy_hash = sha256_text(stable_json({"adapter": "docker-unittest.v1", "config": config.__dict__, "commands": TOOL_COMMANDS}))
        self.calls = 0
        self.deadline = time.monotonic() + config.timeout_seconds

    def command(self, docker: str, tool_id: str, name: str, workspace: Path) -> list[str]:
        if tool_id not in TOOL_COMMANDS or self.config.python_image is None:
            raise StorageError("Tool or pinned image unavailable")
        if not workspace.is_relative_to(self.store.path / "temporary"):
            raise StorageError("Only a sanitized staging snapshot may be mounted")
        safe_path(self.store.path, str(workspace.relative_to(self.store.path)))
        if "," in str(workspace):
            raise StorageError("Comma is not allowed in Docker bind paths")
        # Explicit local socket: do not inherit DOCKER_HOST or a remote context.
        return [docker, "--host", "unix:///var/run/docker.sock", "run", "--rm", "--pull=never",
                "--name", name, "--network=none", "--read-only", "--cap-drop=ALL",
                "--security-opt=no-new-privileges", "--pids-limit=64", "--memory=512m", "--cpus=1",
                "--ulimit", f"fsize={self.config.max_file_bytes}:{self.config.max_file_bytes}",
                "--user", f"{os.getuid()}:{os.getgid()}", "--workdir", "/workspace",
                "--tmpfs", "/tmp:rw,noexec,nosuid,nodev,size=64m", "--env", "HOME=/tmp",
                "--env", "PYTHONDONTWRITEBYTECODE=1", "--mount",
                f"type=bind,source={workspace},target=/workspace,readonly",
                "--entrypoint", "python", self.config.python_image, *TOOL_COMMANDS[tool_id][1:]]

    def run(self, tool_id: str, *, approval_id: str | None = None, dry_run: bool = False) -> dict:
        with self.store.locked():
            run_dir = self.store.new_run()
            result = {"format": "nexonova.tool-result.v1", "tool_id": tool_id, "run_id": run_dir.name,
                      "started_at": utc_now(), "status": "error", "executed": False,
                      "exit_code": None, "tests_run": None, "output": "", "reason": "",
                      "image": self.config.python_image, "sandbox": "docker-local-readonly-no-network",
                      "source_hash": None, "model_usage": "not_applicable", "human_review": "pending"}
            try:
                if tool_id not in TOOL_COMMANDS:
                    raise StorageError("Tool is not allowlisted")
                result["source_hash"] = tree_hash(self.store.workspace)
                if dry_run:
                    result.update(status="needs_user_input", reason="Preview only; no process or approval consumed")
                elif self.calls >= self.config.max_tool_calls or time.monotonic() >= self.deadline:
                    raise StorageError("Tool budget exhausted")
                else:
                    docker = shutil.which("docker")
                    if not docker or self.config.python_image is None:
                        result.update(status="not_answerable", reason="Local Docker and an approved pinned Python image are required")
                    else:
                        self.store.consume_approval(approval_id, tool_id, self.policy_hash)
                        self.calls += 1
                        name = "nexonova-test-" + uuid.uuid4().hex
                        with tempfile.TemporaryDirectory(prefix="test-input-", dir=self.store.path / "temporary") as directory:
                            snapshot = Path(directory)
                            self._snapshot(snapshot, result["source_hash"])
                            command = self.command(docker, tool_id, name, snapshot)
                            result.update(self._execute(command, docker, name))
            except (OSError, ValueError) as exc:
                result.update(status="error", reason=redact(str(exc)))
            result["finished_at"] = utc_now()
            self.store.write(run_dir, "tool-result.json", result)
            self.store.write(run_dir, "state.json", {"format": "nexonova.tool-run.v1", "lifecycle": "finished",
                             "status": result["status"], "tool_result": "tool-result.json"})
            return result

    def _snapshot(self, destination: Path, expected_hash: str) -> None:
        # Source is not mounted: git metadata, dependency caches and credentials stay outside.
        excluded = {"node_modules", ".next", ".git", "__pycache__", ".pytest_cache"}
        for current, directories, filenames in os.walk(self.store.workspace, followlinks=False):
            directories[:] = [name for name in directories if name not in excluded]
            for name in filenames:
                if name == ".git":
                    continue
                relative = str((Path(current) / name).relative_to(self.store.workspace))
                source = safe_path(self.store.workspace, relative)
                content = source.read_bytes()
                if len(content) > self.config.max_file_bytes:
                    raise StorageError("Input file exceeds snapshot budget")
                # Heuristic is deliberately conservative; never log the matched value.
                try:
                    decoded = content.decode("utf-8")
                    if redact(decoded) != decoded:
                        raise StorageError("Potential secret in source; snapshot refused")
                except UnicodeDecodeError:
                    raise StorageError("Binary input is unsupported by the initial unittest adapter")
                target = safe_path(destination, relative)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
        if tree_hash(destination) != expected_hash:
            raise StorageError("Workspace changed while preparing the approved snapshot")

    def _execute(self, command: list[str], docker: str, name: str) -> dict:
        output = bytearray()
        outcome = {"executed": False, "status": "error", "exit_code": None, "reason": "", "tests_run": None}
        # Credentials/config from the operator's home and environment are not inherited.
        with tempfile.TemporaryDirectory(prefix="nexonova-docker-client-") as client_dir:
            env = {"PATH": "/usr/bin:/bin", "HOME": client_dir, "DOCKER_CONFIG": client_dir}
            process = subprocess.Popen(command, cwd=self.store.workspace, env=env, stdin=subprocess.DEVNULL,
                                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                with selectors.DefaultSelector() as selector:
                    selector.register(process.stdout, selectors.EVENT_READ)
                    while selector.get_map():
                        if time.monotonic() >= self.deadline:
                            outcome["reason"] = "timeout"
                            break
                        for key, _ in selector.select(timeout=min(0.1, max(0, self.deadline - time.monotonic()))):
                            chunk = os.read(key.fd, 8192)
                            if not chunk:
                                selector.unregister(key.fileobj)
                            else:
                                output.extend(chunk)
                        if len(output) > self.config.max_output_bytes:
                            outcome["reason"] = "output_limit"
                            break
                    if not outcome["reason"]:
                        try:
                            outcome["exit_code"] = process.wait(timeout=max(0.001, self.deadline - time.monotonic()))
                        except subprocess.TimeoutExpired:
                            outcome["reason"] = "timeout"
            finally:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                process.stdout.close()
                # Kill/remove only this operation's named container, including timeout cases.
                try:
                    cleanup = subprocess.run([docker, "--host", "unix:///var/run/docker.sock", "rm", "-f", name],
                                             env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                             stderr=subprocess.DEVNULL, timeout=10)
                    if cleanup.returncode != 0 and outcome["reason"] in ("timeout", "output_limit"):
                        outcome["reason"] += "; container cleanup requires operator inspection: " + name
                except (OSError, subprocess.TimeoutExpired):
                    outcome["reason"] += "; container cleanup could not be confirmed: " + name
        text = output[:self.config.max_output_bytes].decode("utf-8", errors="replace")
        outcome["output"] = redact(text)
        code = outcome["exit_code"]
        outcome["executed"] = None if code is None else code not in (125, 126, 127)
        matches = re.findall(r"Ran (\d+) tests? in", text)
        outcome["tests_run"] = int(matches[-1]) if matches else None
        if not outcome["reason"]:
            if code == 0 and outcome["tests_run"] and re.search(r"(?m)^OK(?:\s|$)", text):
                outcome["status"] = "complete"
            else:
                outcome["reason"] = "Process failed, tool unavailable, or no successful test execution was reported"
        return outcome
