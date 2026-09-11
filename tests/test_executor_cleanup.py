"""Cleanup must be observed, including Docker auto-remove races."""
from subprocess import CompletedProcess
from unittest.mock import patch
from factory.executor import ToolExecutor


def test_cleanup_waits_for_observed_absence():
    replies = [CompletedProcess([], 0, "container-id\n"), CompletedProcess([], 0, "")]
    with patch("factory.executor.subprocess.run", side_effect=replies) as run:
        assert ToolExecutor._confirm_removed("docker", "test-owned", {})
        assert run.call_count == 2
        assert run.call_args.args[0][-1] == "name=^/test-owned$"


def test_daemon_failure_is_not_absence():
    with patch("factory.executor.subprocess.run", return_value=CompletedProcess([], 1, "")):
        assert not ToolExecutor._confirm_removed("docker", "test-owned", {})


def test_persistent_container_is_not_success():
    with patch("factory.executor.time.monotonic", side_effect=[0, 0, 4]), patch(
        "factory.executor.subprocess.run", return_value=CompletedProcess([], 0, "container-id")):
        assert not ToolExecutor._confirm_removed("docker", "test-owned", {})
