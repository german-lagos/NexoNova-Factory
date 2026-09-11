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
from .execution_scope import execution_order, check_scope
from .storage import ProjectStore, StorageError, tree_hash, safe_path
from .utils import utc_now, sha256_text, stable_json

TOOL_COMMANDS = {"python.unittest": ("python", "-I", "-B", "-m", "unittest", "discover", "-s", "/workspace/tests", "-v")}


def redact(text: str) -> str:
    text = re.sub(r"-----BEGIN [^-]*PRIVATE KEY-----[\s\S]*?(?:-----END [^-]*PRIVATE KEY-----|$)", "[REDACTED KEY]", text)
    # Consume escaped characters, multiline values and unterminated quoted tails.
    # This is heuristic filtering, not a guarantee that arbitrary secrets vanish.
    prefix = r"(?i)((?:password|api[_-]?key|secret|access[_-]?token)[\"']?\s*[=:]\s*)"
    value = r"(?:\"(?:\\(?:[\s\S]|$)|[^\"\\])*(?:\"|$)|'(?:\\(?:[\s\S]|$)|[^'\\])*(?:'|$)|[^\s,;]+)"
    text = re.sub(prefix + value, r"\1[REDACTED]", text)
    text = re.sub(r"(?i)(authorization[\"']?\s*:\s*[\"']?bearer\s+)[^\s,;]+", r"\1[REDACTED]", text)
    return re.sub(r"\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{16,}|glpat-[A-Za-z0-9_-]{16,})\b", "[REDACTED]", text)


class ExecutionInterrupted(KeyboardInterrupt):
    """Propagate interruption only after retaining sanitized partial evidence."""
    def __init__(self, outcome):
        self.outcome = outcome


class ToolExecutor:
    def __init__(self, store: ProjectStore, config: FactoryConfig, *, work_order: dict | None = None) -> None:
        self.store, self.config = store, config
        self.work_order = execution_order(work_order)
        self.policy_hash = sha256_text(stable_json({"adapter": "docker-unittest.v3", "config": config.__dict__, "commands": TOOL_COMMANDS, "work_order": self.work_order}))
        self.calls = 0
        latency = config.timeout_seconds
        if self.work_order is not None:
            latency = min(latency, self.work_order["constraints"]["max_latency_ms"] / 1000)
        self.deadline = time.monotonic() + latency
        self._checkpoint = None

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
            interruption = None
            try:
                if tool_id not in TOOL_COMMANDS:
                    raise StorageError("Tool is not allowlisted")
                result["source_hash"] = tree_hash(self.store.workspace)
                check_scope(self.store, self.work_order)
                if self.work_order is not None:
                    dry_run = dry_run or self.work_order["constraints"]["dry_run"]
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
                        checkpoint = {"format": "nexonova.checkpoint.v1", "phase": "approved", "container": name,
                                      "result": dict(result), "policy_hash": self.policy_hash}
                        def save_partial(partial):
                            checkpoint["phase"] = "executing"
                            checkpoint["result"].update(partial)
                            self.store.write(run_dir, "checkpoint.json", checkpoint)
                        self._checkpoint = save_partial
                        self.store.write(run_dir, "checkpoint.json", checkpoint)
                        with tempfile.TemporaryDirectory(prefix="test-input-", dir=self.store.path / "temporary") as directory:
                            snapshot = Path(directory)
                            checkpoint["staging"] = snapshot.relative_to(self.store.path).as_posix()
                            self.store.write(run_dir, "checkpoint.json", checkpoint)
                            self._snapshot(snapshot, result["source_hash"])
                            command = self.command(docker, tool_id, name, snapshot)
                            result.update(self._execute(command, docker, name))
            except KeyboardInterrupt as exc:
                interruption = exc
                if isinstance(exc, ExecutionInterrupted):
                    result.update(exc.outcome)
                result.update(status="error", termination="interrupted", signal="SIGINT")
                if not isinstance(exc, ExecutionInterrupted):
                    result["reason"] = "interrupted"
            except (OSError, ValueError) as exc:
                result.update(status="error", reason=redact(str(exc)))
            self._checkpoint = None
            result["finished_at"] = utc_now()
            self.store.write(run_dir, "tool-result.json", result)
            self.store.write(run_dir, "state.json", {"format": "nexonova.tool-run.v1", "lifecycle": "finished",
                             "status": result["status"], "tool_result": "tool-result.json"})
            if interruption is not None:
                raise interruption
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
        interrupted = False
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
                                if self._checkpoint is not None:
                                    self._checkpoint({"executed": None, "output": redact(output[:self.config.max_output_bytes].decode("utf-8", errors="replace"))})
                        if len(output) > self.config.max_output_bytes:
                            outcome["reason"] = "output_limit"
                            break
                    if not outcome["reason"]:
                        try:
                            outcome["exit_code"] = process.wait(timeout=max(0.001, self.deadline - time.monotonic()))
                        except subprocess.TimeoutExpired:
                            outcome["reason"] = "timeout"
            except KeyboardInterrupt:
                interrupted = True
                outcome.update(reason="interrupted", termination="interrupted", signal="SIGINT")
            finally:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                if outcome["exit_code"] is None:
                    outcome["exit_code"] = process.returncode
                process.stdout.close()
                # Kill/remove only this operation's named container, including timeout cases.
                try:
                    cleanup = subprocess.run([docker, "--host", "unix:///var/run/docker.sock", "rm", "-f", name],
                                             env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                             stderr=subprocess.DEVNULL, timeout=10)
                    if not self._confirm_removed(docker, name, env):
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
        if interrupted:
            raise ExecutionInterrupted(outcome)
        return outcome

    @staticmethod
    def _confirm_removed(docker: str, name: str, env: dict) -> bool:
        """Observe absence; rm may race with Docker's automatic removal."""
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            check = subprocess.run(
                [docker, "--host", "unix:///var/run/docker.sock", "ps", "-aq",
                 "--filter", "name=^/" + name + "$"], env=env,
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, timeout=1, text=True)
            if check.returncode != 0:
                return False
            if not check.stdout.strip():
                return True
            time.sleep(0.05)
        return False
