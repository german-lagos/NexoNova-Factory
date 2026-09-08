"""Private, single-writer project state. Untrusted processes only see workspace/."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import uuid

from .constants import ROOT
from .utils import atomic_write, stable_json, utc_now


class StorageError(ValueError):
    pass


def checked_root(path: Path) -> Path:
    raw = path.absolute()
    for part in (raw, *raw.parents):
        if part.is_symlink():
            raise StorageError("Symlink workspace root or ancestor is not allowed")
    resolved = raw.resolve()
    if resolved == ROOT or resolved.is_relative_to(ROOT) or ROOT.is_relative_to(resolved):
        raise StorageError("Use a dedicated workspace outside the factory source tree")
    return resolved


def safe_path(root: Path, relative: str) -> Path:
    """Reject ambiguous, traversing, linked and special paths before host I/O."""
    if any(p.is_symlink() for p in (root, *root.parents)):
        raise StorageError("Symlink root or ancestor is not allowed")
    rel = PurePosixPath(relative)
    if not relative or rel.is_absolute() or any(p in ("..", ".", "") for p in relative.split("/")) or "\\" in relative:
        raise StorageError("Expected a canonical relative path")
    path = root
    for part in rel.parts:
        path = path / part
        if path.is_symlink():
            raise StorageError("Symlink not allowed")
        if path.exists():
            info = path.stat()
            if not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
                raise StorageError("Special file not allowed")
            if stat.S_ISREG(info.st_mode) and info.st_nlink != 1:
                raise StorageError("Hardlinked file not allowed")
    if not path.resolve().is_relative_to(root.resolve()):
        raise StorageError("Path escaped its root")
    return path


def tree_hash(root: Path, *, max_files: int = 10000, max_bytes: int = 100_000_000) -> str:
    records = []
    total = 0
    # node_modules is excluded from source baseline; its lockfile is not.
    # The executor independently rejects symlinks crossing the mounted workspace.
    for current, directories, filenames in os.walk(root, followlinks=False):
        for name in list(directories):
            path = Path(current) / name
            if path.is_symlink():
                raise StorageError("Symlink in project source")
            if name in ("node_modules", ".next", ".git", "__pycache__", ".pytest_cache"):
                directories.remove(name)
        for name in sorted(filenames):
            if name == ".git":
                continue
            if (name == ".env" or name.startswith(".env.") and name != ".env.example"
                    or name.endswith((".key", ".pem")) or name in {"id_rsa", "id_ed25519", ".npmrc", ".pypirc"}):
                raise StorageError("Potential credential file must not enter a test workspace")
            path = Path(current) / name
            rel = str(path.relative_to(root))
            safe_path(root, rel)
            total += path.stat().st_size
            if total > max_bytes or len(records) >= max_files:
                raise StorageError("Workspace exceeds inspection budget")
            records.append((rel, hashlib.sha256(path.read_bytes()).hexdigest()))
    return "sha256:" + hashlib.sha256(stable_json(sorted(records)).encode()).hexdigest()


class ProjectStore:
    def __init__(self, root: Path, client_id: str, project_id: str) -> None:
        for value in (client_id, project_id):
            if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,62}", value):
                raise StorageError("Invalid client/project identifier")
        self.root = checked_root(root)
        self.path = safe_path(self.root, f"{client_id}/{project_id}")
        self.client_id, self.project_id = client_id, project_id
        self.workspace = self.path / "workspace"

    def initialize(self) -> None:
        safe_path(self.root, f"{self.client_id}/{self.project_id}")
        for rel in ("workspace", "temporary", "runs", "approvals"):
            safe_path(self.root, f"{self.client_id}/{self.project_id}/{rel}").mkdir(parents=True, exist_ok=True, mode=0o700)

    @contextmanager
    def locked(self):
        self.initialize()
        path = safe_path(self.path, ".writer.lock")
        fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise StorageError("Project already has an active writer") from exc
            yield self
        finally:
            os.close(fd)

    def new_run(self) -> Path:
        self.initialize()
        path = safe_path(self.path, "runs/RUN-" + uuid.uuid4().hex)
        path.mkdir(mode=0o700)
        self.write(path, "state.json", {"format": "nexonova.tool-run.v1", "lifecycle": "running", "started_at": utc_now()})
        return path

    def write(self, directory: Path, relative: str, payload: dict) -> None:
        if not directory.resolve().is_relative_to(self.path.resolve()):
            raise StorageError("Directory belongs to another project")
        safe_path(self.path, str(directory.relative_to(self.path)))
        atomic_write(safe_path(directory, relative), json.dumps(payload, ensure_ascii=True, indent=2, allow_nan=False) + "\n")

    def approve_tool(self, tool_id: str, *, actor: str, policy_hash: str, ttl_seconds: int = 600) -> str:
        """Host operator API; not exposed inside the process sandbox or model context."""
        if not re.fullmatch(r"sha256:[a-f0-9]{64}", policy_hash):
            raise StorageError("Invalid execution-policy hash")
        if not actor.strip() or len(actor) > 100 or not 1 <= ttl_seconds <= 3600:
            raise StorageError("Invalid approval actor or TTL")
        with self.locked():
            approval_id = uuid.uuid4().hex
            self.write(self.path / "approvals", approval_id + ".json", {
                "id": approval_id, "tool_id": tool_id, "actor": actor,
                "client_id": self.client_id, "project_id": self.project_id,
                "workspace_hash": tree_hash(self.workspace), "policy_hash": policy_hash, "used": False,
                "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)).isoformat(),
            })
            return approval_id

    def consume_approval(self, approval_id: str | None, tool_id: str, policy_hash: str) -> None:
        if not approval_id or not re.fullmatch(r"[a-f0-9]{32}", approval_id):
            raise StorageError("A host-operator approval is required")
        path = safe_path(self.path, f"approvals/{approval_id}.json")
        try:
            approval = json.loads(path.read_text())
            if approval["used"] or approval["tool_id"] != tool_id or approval.get("policy_hash") != policy_hash or approval["workspace_hash"] != tree_hash(self.workspace):
                raise StorageError("Approval already used or action/workspace changed")
            if approval["client_id"] != self.client_id or approval["project_id"] != self.project_id:
                raise StorageError("Approval belongs to another project")
            if datetime.fromisoformat(approval["expires_at"]) <= datetime.now(timezone.utc):
                raise StorageError("Approval expired")
        except (OSError, KeyError, TypeError, ValueError) as exc:
            raise StorageError("Invalid approval: " + str(exc)) from exc
        approval["used"] = True
        self.write(self.path / "approvals", path.name, approval)
