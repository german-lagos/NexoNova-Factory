"""P2 behavioral validation. Trusted host fixtures do NOT certify Docker isolation.

Known failures remain ordinary failing tests, not xfail or relaxed assertions.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

from factory.config import FactoryConfig
from factory.executor import ToolExecutor
from factory.storage import ProjectStore, StorageError, tree_hash
from factory.utils import read_json


@pytest.fixture
def store(tmp_path):
    value = ProjectStore(tmp_path / "private", "client-a", "site")
    value.initialize()
    (value.workspace / "input.txt").write_text("public fixture")
    return value


def host_adapter(store, monkeypatch, source):
    """Replace only container transport with trusted Python; retain run persistence."""
    executor = ToolExecutor(store, FactoryConfig(python_image="python@sha256:" + "a" * 64))
    monkeypatch.setattr("factory.executor.shutil.which", lambda _: "/usr/bin/true")
    monkeypatch.setattr(executor, "command", lambda *args: [sys.executable, "-I", "-B", "-c", source])
    approval = store.approve_tool("python.unittest", actor="synthetic-operator", policy_hash=executor.policy_hash)
    return executor, approval


def test_real_host_cwd_environment_streams_and_failure(store, monkeypatch):
    monkeypatch.setenv("NEXONOVA_SYNTHETIC_SECRET", "synthetic-only")
    source = "import os,sys,json; print(json.dumps({'cwd':os.getcwd(),'env':dict(os.environ)}),flush=True); print('stderr-marker',file=sys.stderr); sys.exit(7)"
    executor, approval = host_adapter(store, monkeypatch, source)
    result = executor.run("python.unittest", approval_id=approval)
    observed = json.loads(result["output"].splitlines()[0])
    assert observed["cwd"] == str(store.workspace)
    assert "NEXONOVA_SYNTHETIC_SECRET" not in observed["env"]
    # Python may inject LC_CTYPE during locale coercion after execve.
    assert set(observed["env"]) <= {"PATH", "HOME", "DOCKER_CONFIG", "LC_CTYPE"}
    assert observed["env"]["PATH"] == "/usr/bin:/bin"
    assert observed["env"]["HOME"] == observed["env"]["DOCKER_CONFIG"]
    assert not Path(observed["env"]["HOME"]).exists()
    assert "stderr-marker" in result["output"]
    assert result["exit_code"] == 7 and result["status"] == "error"
    assert read_json(store.path / "runs" / result["run_id"] / "tool-result.json") == result
    assert not list((store.path / "temporary").iterdir())


def test_real_missing_executable_persists_error_and_cleans_staging(store, monkeypatch):
    executor, approval = host_adapter(store, monkeypatch, "")
    monkeypatch.setattr(executor, "command", lambda *args: [str(store.path / "absent-executable")])
    result = executor.run("python.unittest", approval_id=approval)
    assert result["status"] == "error" and result["exit_code"] is None
    assert not result["executed"]
    assert read_json(store.path / "runs" / result["run_id"] / "state.json")["lifecycle"] == "finished"
    assert not list((store.path / "temporary").iterdir())


def test_real_unittest_success_is_persisted(store, monkeypatch):
    tests = store.workspace / "tests"
    tests.mkdir()
    (tests / "test_fixture.py").write_text("import unittest\nclass Fixture(unittest.TestCase):\n def test_sum(self): self.assertEqual(2+3,5)\n")
    executor, approval = host_adapter(store, monkeypatch, "")
    monkeypatch.setattr(executor, "command", lambda *args: [sys.executable, "-I", "-B", "-m", "unittest", "discover", "-s", str(tests), "-v"])
    result = executor.run("python.unittest", approval_id=approval)
    assert result["status"] == "complete" and result["exit_code"] == 0
    assert result["tests_run"] == 1 and result["executed"] is True
    assert read_json(store.path / "runs" / result["run_id"] / "tool-result.json") == result


def test_timeout_reaps_real_host_child(store):
    pid_path = store.path / "child.pid"
    source = f"import os,time; from pathlib import Path; Path({str(pid_path)!r}).write_text(str(os.getpid())); time.sleep(20)"
    executor = ToolExecutor(store, FactoryConfig(timeout_seconds=1))
    started = time.monotonic()
    result = executor._execute([sys.executable, "-I", "-B", "-c", source], "/usr/bin/true", "synthetic-no-container")
    assert result["status"] == "error" and "timeout" in result["reason"]
    assert time.monotonic() - started < 5
    with pytest.raises(ProcessLookupError):
        os.kill(int(pid_path.read_text()), 0)


@pytest.mark.parametrize("change", ["missing", "content", "policy", "client"])
def test_approval_rejection_precedes_any_process(store, monkeypatch, change):
    executor, approval = host_adapter(store, monkeypatch, "raise SystemExit('must never run')")
    if change == "missing":
        approval = None
    elif change == "content":
        (store.workspace / "input.txt").write_text("changed scope")
    elif change == "policy":
        executor.policy_hash = "sha256:" + "b" * 64
    else:
        other = ProjectStore(store.root, "client-b", "site")
        other.initialize()
        executor.store = other
    def forbidden(*args, **kwargs):
        pytest.fail("Rejected approval started a process")
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    result = executor.run("python.unittest", approval_id=approval)
    assert result["status"] == "error" and result["executed"] is False


@pytest.mark.parametrize("relative", ["../outside.json", "/tmp/outside.json", "link/outside.json"])
def test_rejected_write_preserves_external_directory(store, tmp_path, relative):
    outside = tmp_path / "outside"
    outside.mkdir()
    (store.path / "runs" / "link").symlink_to(outside, target_is_directory=True)
    with pytest.raises(StorageError):
        store.write(store.path / "runs", relative, {"unexpected": True})
    assert list(outside.iterdir()) == []
    assert not (store.path / "outside.json").exists()


def test_lock_excludes_real_second_process(store):
    source = "from pathlib import Path; from factory.storage import ProjectStore,StorageError; import sys\ns=ProjectStore(Path(sys.argv[1]),'client-a','site')\ntry:\n with s.locked(): s.new_run()\nexcept StorageError: sys.exit(23)\n"
    with store.locked():
        result = subprocess.run([sys.executable, "-B", "-c", source, str(store.root)], capture_output=True, timeout=10)
    assert result.returncode == 23, result.stderr.decode()
    assert not list((store.path / "runs").iterdir())
    with store.locked():
        assert store.new_run().exists()


def test_real_output_secret_is_absent_from_persisted_logs(store, monkeypatch):
    executor, approval = host_adapter(store, monkeypatch, "print('password=synthetic-single-value')")
    result = executor.run("python.unittest", approval_id=approval)
    log = (store.path / "runs" / result["run_id"] / "tool-result.json").read_text()
    assert "synthetic-single-value" not in log


def test_quoted_secret_with_spaces_is_fully_redacted_in_logs(store, monkeypatch):
    executor, approval = host_adapter(store, monkeypatch, "print('{\"password\": \"synthetic-head synthetic-private-tail\"}')")
    result = executor.run("python.unittest", approval_id=approval)
    log = (store.path / "runs" / result["run_id"] / "tool-result.json").read_text()
    leaked = "synthetic-private-tail" in log
    assert not leaked, "Quoted synthetic secret suffix survives in persisted ToolResult"


def test_sigint_leaves_recoverable_finished_run(store):
    # SIGINT targets an isolated driver, never pytest. Its trusted child sleeps
    # so the executor must reap it during interruption. No Docker is invoked.
    source = '''
import os, sys
from pathlib import Path
from factory.config import FactoryConfig
from factory.executor import ToolExecutor
from factory.storage import ProjectStore
import factory.executor as module
s = ProjectStore(Path(sys.argv[1]), "client-a", "site")
e = ToolExecutor(s, FactoryConfig(python_image="python@sha256:" + "a" * 64))
module.shutil.which = lambda _: "/usr/bin/true"
child = "import os,signal,time; os.kill(os.getppid(),signal.SIGINT); time.sleep(10)"
e.command = lambda *args: [sys.executable, "-I", "-B", "-c", child]
a = s.approve_tool("python.unittest", actor="synthetic-operator", policy_hash=e.policy_hash)
e.run("python.unittest", approval_id=a)
'''
    before = tree_hash(store.workspace)
    driver = subprocess.run([sys.executable, "-B", "-c", source, str(store.root)], capture_output=True, timeout=15)
    assert driver.returncode != 0
    assert tree_hash(store.workspace) == before
    assert not list((store.path / "temporary").iterdir())
    runs = list((store.path / "runs").iterdir())
    assert len(runs) == 1
    state = read_json(runs[0] / "state.json")
    assert state["lifecycle"] == "finished", "SIGINT leaves running state without terminal ToolResult"
    assert read_json(runs[0] / "tool-result.json")["status"] == "error"
