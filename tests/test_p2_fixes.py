"""Regression coverage with synthetic values and trusted host processes only."""
import os
import json
from dataclasses import replace
from pathlib import Path
import subprocess
import sys

import pytest

from factory.executor import redact, ToolExecutor
from factory.config import FactoryConfig
from factory.utils import read_json
from test_p2_validation import store, host_adapter


@pytest.mark.parametrize("value", [
    "'synthetic head tail'", '\"synthetic head tail\"',
    r"'synthetic \' tail'", r'"synthetic \" tail"',
    '"synthetic\nmultiline tail"', 'synthetic-simple',
    '"synthetic unfinished tail', "'synthetic unfinished tail",
    '"synthetic trailing\\',
])
def test_secret_value_formats(value):
    filtered = redact("password=" + value)
    assert "synthetic" not in filtered and "tail" not in filtered
    assert "[REDACTED]" in filtered


def test_truncated_quoted_output_is_redacted(store, monkeypatch):
    executor, approval = host_adapter(store, monkeypatch, "print('password=\"' + 'synthetic-tail '*1000)")
    executor.config = replace(executor.config, max_output_bytes=1024)
    result = executor.run("python.unittest", approval_id=approval)
    assert "output_limit" in result["reason"]
    assert "synthetic-tail" not in result["output"]


def test_sigint_partial_evidence_cli_exit_and_cleanup(store):
    driver = r'''import os, sys
from pathlib import Path
import factory.executor as module
from factory.executor import ToolExecutor
from factory.config import FactoryConfig
from factory.storage import ProjectStore
from factory.cli import main
s=ProjectStore(Path(sys.argv[1]), "client-a", "site")
e=ToolExecutor(s, FactoryConfig(python_image="python@sha256:"+"a"*64))
module.shutil.which=lambda _: "/usr/bin/true"
child="import os,signal,time,json; print(json.dumps({'pid':os.getpid(),'home':os.environ['HOME']}),flush=True); print('public-evidence',flush=True); print('password=synthetic-only',flush=True); time.sleep(0.2); os.kill(os.getppid(),signal.SIGINT); time.sleep(10)"
e.command=lambda *args: [sys.executable,"-I","-B","-c",child]
a=s.approve_tool("python.unittest",actor="test",policy_hash=e.policy_hash)
import factory.cli as cli
cli.cmd_list=lambda args: e.run("python.unittest",approval_id=a)
sys.exit(main(["list"]))
'''
    result = subprocess.run([sys.executable, "-B", "-c", driver, str(store.root)], capture_output=True, timeout=15)
    assert result.returncode == 130
    run = next((store.path / "runs").iterdir())
    outcome = read_json(run / "tool-result.json")
    assert outcome["termination"] == "interrupted" and outcome["signal"] == "SIGINT"
    assert outcome["status"] == "error" and outcome["reason"] == "interrupted"
    assert "public-evidence" in outcome["output"] and "synthetic-only" not in outcome["output"]
    assert read_json(run / "state.json")["lifecycle"] == "finished"
    assert not list((store.path / "temporary").iterdir())

    resources = json.loads(outcome["output"].splitlines()[0])
    assert not Path(resources["home"]).exists()
    with pytest.raises(ProcessLookupError):
        os.kill(resources["pid"], 0)
