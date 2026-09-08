from pathlib import Path

import pytest

from factory.cli import main, detect_tools
from factory.context import ContextManager
from factory.constants import DESIGN_DOCS
from factory.orchestrator import OrchestratorGraph
from factory.reports import verify_run
from factory.registry import agent_registry
from factory.schemas import SchemaError, validate_strict
from factory.utils import read_json, write_json
from factory.validators import ValidatorChain
from test_factory import _state


def check(tmp_path, output, gates=("evidence",)):
    return ValidatorChain.status_from_items(ValidatorChain().validate_output(
        state=_state(), output=output, required_gates=gates, run_dir=tmp_path))


def test_fabricated_evidence_is_rejected(tmp_path):
    assert check(tmp_path, {"critical_claims": [{"evidence_id": "EV-NOT-REAL"}], "evidence_refs": ["EV-NOT-REAL"]}) == "not_answerable"


def test_consumed_evidence_hash_and_reference_are_checked(tmp_path):
    source = tmp_path / "sources"
    source.mkdir()
    (source / DESIGN_DOCS[0]).write_text("## Policy\n" + "harness policy " * 400)
    run = tmp_path / "run"
    ContextManager(source).write_context_pack(run, "policy")
    output = {"evidence_refs": ["EV-001"], "critical_claims": [{"evidence_id": "EV-001"}]}
    assert check(run, output) == "complete"
    pack = read_json(run / "context-pack.json")
    pack["chunks"][0]["content"] += "tampered"
    write_json(run / "context-pack.json", pack)
    assert check(run, output) == "not_answerable"


@pytest.mark.parametrize("gate", ["tests", "security", "coverage", "final_format", "unknown", "consistency"])
def test_unimplemented_required_gate_cannot_pass(tmp_path, gate):
    assert check(tmp_path, {"coverage": "complete", "drift_detected": False}, (gate,)) == "error"


@pytest.mark.parametrize("used,limit", [("used_input_tokens", "max_input_tokens"), ("used_output_tokens", "max_output_tokens")])
def test_token_overrun_rejected(tmp_path, used, limit):
    state = _state()
    state["budget"][used] = state["budget"][limit] + 1
    items = ValidatorChain().validate_output(state=state, output={}, required_gates=("budget",), run_dir=tmp_path)
    assert ValidatorChain.status_from_items(items) == "error"


def test_nonfinite_number_is_invalid():
    with pytest.raises(SchemaError):
        validate_strict({"type": "number"}, float("nan"))


def test_legacy_agents_are_not_advertised_as_production():
    assert all(a.status == "legacy" for a in agent_registry().values())
    assert not any(t["available"] for t in detect_tools().values())


def test_failed_run_has_honest_closure_and_cannot_be_promoted(tmp_path):
    root = tmp_path / "factory"
    root.mkdir()
    run = OrchestratorGraph(factory_root=root, project_dir=tmp_path / "project").run("diagnostic")
    final = read_json(run / "final-report.json")
    assert final["status"] == "not_answerable"
    assert final["ready_for_first_project"] is False
    assert "not_answerable" in (run / "traceability-matrix.md").read_text()
    assert read_json(run / "billing-ledger.json")["model_calls"] == 0
    final["status"] = "complete"
    write_json(run / "final-report.json", final)
    assert verify_run(run)["status"] == "error"
    assert any("hash" in i for i in verify_run(run)["issues"])


def test_cli_failed_run_returns_nonzero(tmp_path):
    assert main(["run", "--project", str(tmp_path / "p"), "--objective", "diagnostic"]) == 1


def test_verify_invalid_json_returns_report(tmp_path):
    (tmp_path / "final-report.json").write_text("{broken")
    assert verify_run(tmp_path)["status"] == "error"
