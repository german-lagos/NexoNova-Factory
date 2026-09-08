"""Run closure and read-only verification; no self-reported quality certification."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .constants import FACTORY_VERSION
from .storage import safe_path
from .schemas import AGENT_RESULT_SCHEMA, CYCLE_STATE_SCHEMA, WORK_ORDER_SCHEMA, validate_strict
from .utils import read_json, sha256_file, sha256_text, stable_json, write_json

RUN_FORMAT = "nexonova.run.v1"
REQUIRED = ("work_order.json", "state.json", "final-report.json", "validation-report.json",
            "traceability-matrix.md", "RUN_STATE.md", "DECISIONS.md", "ERRORS.md", "billing-ledger.json")


def finalize_run(run_dir: Path, state: dict[str, Any], results: list[dict[str, Any]], *, expected_cycles: int) -> None:
    status = state["status"]
    if status == "complete" and (len(results) != expected_cycles or any(r["status"] != "complete" for r in results)):
        status = "error"
    state["status"] = status
    write_json(run_dir / "state.json", state)
    validation = {"status": status, "expected_cycles": expected_cycles,
                  "results": [{"cycle_id": r["cycle_id"], "agent_id": r["agent_id"], "status": r["status"],
                               "validation": r["validation"]["status"]} for r in results]}
    write_json(run_dir / "validation-report.json", validation)
    write_json(run_dir / "final-report.json", {
        "format": RUN_FORMAT, "run_id": state["run_id"], "status": status,
        "factory_version": FACTORY_VERSION, "agents_executed": [r["agent_id"] for r in results],
        "ready_for_first_project": False, "scope": "legacy_bootstrap_diagnostic",
        "human_review": "pending", "artifacts_dir": ".",
    })
    lines = ["# Execution trace", "", "No requirement coverage is inferred from these records.", "",
             "| Cycle | Agent | Outcome |", "|---|---|---|"]
    lines += [f'| {r["cycle_id"]} | {r["agent_id"]} | {r["status"]} |' for r in results]
    (run_dir / "traceability-matrix.md").write_text("\n".join(lines) + "\n")
    (run_dir / "RUN_STATE.md").write_text(f"# Run state\n\nOutcome: {status}.\nProduct readiness: not certified.\n")
    (run_dir / "DECISIONS.md").write_text("# Decisions\n\nHuman review pending. No approvals inferred.\n")
    issues = [str(r["output"].get("error", r["validation"])) for r in results if r["status"] != "complete"]
    (run_dir / "ERRORS.md").write_text("# Issues\n\n" + ("\n".join(issues) if issues else "No failed cycles recorded; not a security certification.") + "\n")
    if not (run_dir / "billing-ledger.json").exists():
        write_json(run_dir / "billing-ledger.json", {"measurement": "no_model_calls", "model_calls": 0,
                   "input_tokens": 0, "output_tokens": 0, "cost_usd": 0, "tool_executions": 0})
    files = {str(p.relative_to(run_dir)): sha256_file(p) for p in sorted(run_dir.rglob("*"))
             if p.is_file() and p.suffix != ".jsonl" and p.name != "run-manifest.json"}
    write_json(run_dir / "run-manifest.json", {"format": RUN_FORMAT, "files": files})


def verify_run(run_dir: Path) -> dict[str, Any]:
    """Integrity and outcome checks, not proof against an attacker rewriting the whole run."""
    result: dict[str, Any] = {"status": "error", "run_dir": str(run_dir), "missing": [], "issues": [], "final_status": "error"}
    try:
        if run_dir.is_symlink():
            raise ValueError("Linked run directory")
        for name in (*REQUIRED, "run-manifest.json"):
            safe_path(run_dir, name)
    except ValueError as exc:
        result["issues"].append(str(exc))
        return result
    result["missing"] = [name for name in (*REQUIRED, "run-manifest.json") if not (run_dir / name).is_file()]
    if result["missing"]:
        result["issues"].append("Missing required artifacts or unsupported legacy run format")
        return result
    try:
        manifest = read_json(run_dir / "run-manifest.json")
        if manifest["format"] != RUN_FORMAT or not set(REQUIRED) <= set(manifest["files"]):
            raise ValueError("Invalid run manifest")
        for name, digest in manifest["files"].items():
            path = safe_path(run_dir, name)
            if Path(name).is_absolute() or ".." in Path(name).parts or not path.resolve().is_relative_to(run_dir.resolve()) or path.is_symlink():
                raise ValueError("Invalid artifact path")
            if sha256_file(path) != digest:
                raise ValueError("Artifact hash mismatch: " + name)
        state, final, validation = (read_json(run_dir / name) for name in ("state.json", "final-report.json", "validation-report.json"))
        validate_strict(WORK_ORDER_SCHEMA, read_json(run_dir / "work_order.json"))
        validate_strict(CYCLE_STATE_SCHEMA, state)
        result["final_status"] = final["status"]
        if final["format"] != RUN_FORMAT or state["run_id"] != final["run_id"]:
            raise ValueError("Run identity mismatch")
        records = [read_json(p) for p in sorted((run_dir / "agent-results").glob("*.json"))]
        expected = validation["expected_cycles"]
        if len(records) != expected or len(validation["results"]) != expected:
            raise ValueError("Workflow not fully executed")
        for record in records:
            validate_strict(AGENT_RESULT_SCHEMA, record)
            if record["run_id"] != state["run_id"] or record["status"] != "complete" or record["validation"]["status"] != "complete":
                raise ValueError("Unsuccessful cycle")
            if record["logs"]["output_hash"] != sha256_text(stable_json(record["output"])):
                raise ValueError("Output hash mismatch")
            if not record["validation"].get("items") or any(i["status"] != "complete" for i in record["validation"]["items"]):
                raise ValueError("Missing or failed validation items")
        if not records or {state["status"], final["status"], validation["status"]} != {"complete"}:
            raise ValueError("Run outcome is not complete")
        result["status"] = "complete"
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        result["issues"].append(str(exc))
    return result
