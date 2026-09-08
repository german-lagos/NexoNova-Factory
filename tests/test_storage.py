from datetime import datetime, timedelta, timezone
import os
from pathlib import Path

import pytest

from factory.config import FactoryConfig
from factory.constants import ROOT
from factory.context import ContextManager
from factory.executor import ToolExecutor, redact
from factory.memory import MemoryGate
from factory.storage import ProjectStore, StorageError, atomic_write, safe_path, tree_hash
from factory.utils import read_json, write_json

POLICY_HASH = "sha256:" + "b" * 64


@pytest.fixture
def store(tmp_path):
    result = ProjectStore(tmp_path / "private", "acme", "site")
    result.initialize()
    (result.workspace / "requirements.txt").write_text("synthetic input\n")
    return result


@pytest.mark.parametrize("relative", ["../other", "/tmp/file", "x/../../other", "./x", "x//y", "x\\y"])
def test_escape_paths_rejected(store, relative):
    with pytest.raises(StorageError):
        safe_path(store.workspace, relative)


def test_factory_source_cannot_be_workspace():
    with pytest.raises(StorageError):
        ProjectStore(ROOT / "projects", "acme", "site")


def test_symlink_and_hardlink_are_rejected(store, tmp_path):
    outside = tmp_path / "outside"
    outside.write_text("must not be modified")
    (store.workspace / "link").symlink_to(outside)
    with pytest.raises(StorageError):
        safe_path(store.workspace, "link")
    os.link(outside, store.workspace / "hardlink")
    with pytest.raises(StorageError):
        safe_path(store.workspace, "hardlink")
    assert outside.read_text() == "must not be modified"


def test_replaced_project_directory_is_rejected(store, tmp_path):
    other = tmp_path / "other"
    other.mkdir()
    (store.path / "runs").rmdir()
    (store.path / "runs").symlink_to(other, target_is_directory=True)
    with pytest.raises(StorageError):
        store.new_run()
    assert list(other.iterdir()) == []


def test_cross_client_directory_write_is_rejected(store):
    other = ProjectStore(store.root, "other", "site")
    other.initialize()
    with pytest.raises(StorageError):
        store.write(other.path / "runs", "result.json", {})


def test_writer_lock_and_unique_runs(store):
    with store.locked():
        with pytest.raises(StorageError):
            with store.locked():
                pass
        one, two = store.new_run(), store.new_run()
    assert one != two
    with store.locked():
        assert read_json(one / "state.json")["lifecycle"] == "running"


def test_atomic_failure_preserves_last_state(tmp_path, monkeypatch):
    path = tmp_path / "state.json"
    atomic_write(path, '{"status":"previous"}')
    def fail(*args):
        raise OSError("simulated interrupted replacement")
    monkeypatch.setattr(os, "replace", fail)
    with pytest.raises(OSError):
        atomic_write(path, '{"status":"next"}')
    assert read_json(path)["status"] == "previous"
    assert len(list(tmp_path.iterdir())) == 1


def test_approval_is_bound_to_content_action_and_consumed(store):
    approval = store.approve_tool("python.unittest", actor="test-operator", policy_hash=POLICY_HASH)
    with pytest.raises(StorageError):
        store.consume_approval(approval, "other.tool", POLICY_HASH)
    with store.locked():
        store.consume_approval(approval, "python.unittest", POLICY_HASH)
        with pytest.raises(StorageError):
            store.consume_approval(approval, "python.unittest", POLICY_HASH)
    approval = store.approve_tool("python.unittest", actor="test-operator", policy_hash=POLICY_HASH)
    (store.workspace / "requirements.txt").write_text("changed input")
    with pytest.raises(StorageError):
        store.consume_approval(approval, "python.unittest", POLICY_HASH)


def test_expired_or_cross_client_approval_rejected(store):
    approval = store.approve_tool("python.unittest", actor="test-operator", policy_hash=POLICY_HASH)
    path = store.path / "approvals" / (approval + ".json")
    record = read_json(path)
    record["expires_at"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    write_json(path, record)
    with pytest.raises(StorageError):
        store.consume_approval(approval, "python.unittest", POLICY_HASH)
    other = ProjectStore(store.root, "other", "site")
    other.initialize()
    with pytest.raises(StorageError):
        other.consume_approval(approval, "python.unittest", POLICY_HASH)


def test_memory_read_never_initializes_factory_root(tmp_path):
    source, project = tmp_path / "factory", tmp_path / "project"
    source.mkdir()
    project.mkdir()
    gate = MemoryGate(source, project)
    assert gate.read_report(project / "run")["loaded_records"] == []
    assert list(source.iterdir()) == []
    assert gate.propose(project / "run", {"approval_status": "approved"})["status"] == "needs_user_input"


def test_context_snapshots_cannot_be_overwritten(tmp_path):
    source = tmp_path / "sources"
    source.mkdir()
    (source / "guide.md").write_text("## Rules\nExplicit project evidence")
    context = ContextManager(source, sources=("guide.md",))
    first = context.write_context_pack(tmp_path / "cycle-one", "evidence")
    (source / "guide.md").write_text("## Changed\nNew evidence")
    with pytest.raises(ValueError):
        context.write_context_pack(tmp_path / "cycle-one", "evidence")
    context.write_context_pack(tmp_path / "cycle-two", "evidence")
    assert read_json(tmp_path / "cycle-one/context-pack.json") == first


def test_preview_has_no_process_and_keeps_approval(store, monkeypatch):
    before = tree_hash(store.workspace)
    approval = store.approve_tool("python.unittest", actor="test-operator", policy_hash=POLICY_HASH)
    def forbidden(*args, **kwargs):
        pytest.fail("No subprocess should start")
    monkeypatch.setattr("subprocess.Popen", forbidden)
    result = ToolExecutor(store, FactoryConfig()).run("python.unittest", approval_id=approval, dry_run=True)
    assert result["status"] == "needs_user_input" and not result["executed"]
    assert tree_hash(store.workspace) == before
    assert read_json(store.path / "approvals" / (approval + ".json"))["used"] is False


def test_missing_docker_never_falls_back_to_host_execution(store, monkeypatch):
    monkeypatch.setattr("factory.executor.shutil.which", lambda command: None)
    result = ToolExecutor(store, FactoryConfig()).run("python.unittest")
    assert result["status"] == "not_answerable"
    assert result["executed"] is False and result["exit_code"] is None
    assert read_json(store.path / "runs" / result["run_id"] / "state.json")["lifecycle"] == "finished"


def test_free_shell_and_missing_approval_are_blocked(store, monkeypatch):
    monkeypatch.setattr("factory.executor.shutil.which", lambda command: "/usr/bin/docker")
    executor = ToolExecutor(store, FactoryConfig(python_image="python@sha256:" + "a" * 64))
    assert executor.run("shell.free")["status"] == "error"
    result = executor.run("python.unittest")
    assert result["status"] == "error" and result["executed"] is False


def test_tool_call_budget_prevents_execution(store):
    executor = ToolExecutor(store, FactoryConfig())
    executor.calls = executor.config.max_tool_calls
    result = executor.run("python.unittest")
    assert result["status"] == "error" and result["executed"] is False


def test_docker_command_never_mounts_approvals_or_host_credentials(store):
    executor = ToolExecutor(store, FactoryConfig(python_image="python@sha256:" + "a" * 64))
    snapshot = store.path / "temporary" / "snapshot"
    snapshot.mkdir()
    command = executor.command("/usr/bin/docker", "python.unittest", "nexonova-test-fixture", snapshot)
    assert "--pull=never" in command and "--network=none" in command
    assert "--read-only" in command and "--cap-drop=ALL" in command
    assert f"type=bind,source={snapshot},target=/workspace,readonly" in command
    assert not any("approvals" in part for part in command)
    assert command[1:3] == ["--host", "unix:///var/run/docker.sock"]


def test_invalid_config_and_untrusted_approval_rejected(tmp_path):
    path = tmp_path / "config.json"
    write_json(path, {"approved": True})
    with pytest.raises(StorageError):
        FactoryConfig.load(path)
    for changes in ({"timeout_seconds": -1}, {"memory_enabled": True}, {"python_image": "python:latest"}):
        with pytest.raises(StorageError):
            FactoryConfig(**changes)


def test_secret_redaction_uses_synthetic_values_only():
    assert "synthetic-value" not in redact("password=synthetic-value Authorization: Bearer synthetic-value")


def test_negative_budget_and_path_identifiers_rejected():
    from factory.schemas import CYCLE_STATE_SCHEMA, SchemaError, validate_strict
    from test_factory import _state
    for field, value in (("cycle_id", "../../escape"), ("run_id", "RUN-../escape")):
        state = _state()
        state[field] = value
        with pytest.raises(SchemaError):
            validate_strict(CYCLE_STATE_SCHEMA, state)
    state = _state()
    state["budget"]["used_input_tokens"] = -1
    with pytest.raises(SchemaError):
        validate_strict(CYCLE_STATE_SCHEMA, state)


def test_json_invalid_numbers_do_not_replace_state(tmp_path):
    path = tmp_path / "state.json"
    write_json(path, {"value": 1})
    with pytest.raises(ValueError):
        write_json(path, {"value": float("nan")})
    assert read_json(path) == {"value": 1}


def test_legacy_policy_boolean_cannot_authorize_write():
    from factory.policy import PolicyEngine
    from factory.registry import agent_registry, tool_registry
    decision = PolicyEngine(tool_registry()).check_tool(
        agent_registry()["agent.spec_detallada"], "tool.cache.set", {"approved": True})
    assert decision.status == "needs_user_input"


def test_failed_client_init_does_not_touch_factory():
    from factory.cli import main
    assert main(["init-project", "--project", str(ROOT / "project")]) == 2


def test_executor_reader_handles_timeout_and_redacts_output(store):
    # Trusted synthetic host subprocess tests the stream limiter, not Docker isolation.
    import sys
    executor = ToolExecutor(store, FactoryConfig(timeout_seconds=1))
    outcome = executor._execute([sys.executable, "-I", "-c", "import time;print('password=synthetic-value',flush=True);time.sleep(5)"],
                                "/usr/bin/true", "synthetic-test-no-container")
    assert outcome["status"] == "error" and "timeout" in outcome["reason"]
    assert "synthetic-value" not in outcome["output"]


def test_executor_reader_bounds_output(store):
    import sys
    executor = ToolExecutor(store, FactoryConfig(max_output_bytes=1024))
    outcome = executor._execute([sys.executable, "-I", "-c", "print('x'*20000)"],
                                "/usr/bin/true", "synthetic-test-no-container")
    assert outcome["status"] == "error" and "output_limit" in outcome["reason"]
    assert len(outcome["output"]) <= 1024


def test_zero_reported_tests_cannot_pass(store):
    import sys
    executor = ToolExecutor(store, FactoryConfig())
    outcome = executor._execute([sys.executable, "-I", "-c", "print('Ran 0 tests in 0.1s\\nOK')"],
                                "/usr/bin/true", "synthetic-test-no-container")
    assert outcome["status"] == "error"
    assert outcome["tests_run"] == 0


def test_snapshot_excludes_git_and_never_copies_credential_files(store):
    (store.workspace / ".git").mkdir()
    (store.workspace / ".git" / "config").write_text("private repository metadata")
    snapshot = store.path / "temporary" / "snapshot"
    snapshot.mkdir()
    executor = ToolExecutor(store, FactoryConfig())
    executor._snapshot(snapshot, tree_hash(store.workspace))
    assert not (snapshot / ".git").exists()
    (store.workspace / ".env").write_text("synthetic credential file")
    with pytest.raises(StorageError):
        tree_hash(store.workspace)


def test_source_secret_is_not_copied(store):
    (store.workspace / "sample.py").write_text('password="synthetic-value"')
    snapshot = store.path / "temporary" / "snapshot"
    snapshot.mkdir()
    with pytest.raises(StorageError):
        ToolExecutor(store, FactoryConfig())._snapshot(snapshot, tree_hash(store.workspace))
    assert not (snapshot / "sample.py").exists()


def test_redaction_handles_json_and_truncated_private_key():
    assert "synthetic-value" not in redact('{"password": "synthetic-value"}')
    assert "synthetic-value" not in redact("-----BEGIN PRIVATE KEY-----\nsynthetic-value")


def test_changed_execution_policy_invalidates_approval(store):
    approval = store.approve_tool("python.unittest", actor="test-operator", policy_hash=POLICY_HASH)
    with pytest.raises(StorageError):
        store.consume_approval(approval, "python.unittest", "sha256:" + "c" * 64)
