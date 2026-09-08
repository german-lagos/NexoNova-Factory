from __future__ import annotations

from pathlib import Path
import uuid
from typing import Any

from .constants import FACTORY_VERSION, MEMORY_VERSION, POLICY_VERSION, ROOT, TOOL_REGISTRY_VERSION, WORKFLOW_VERSION
from .harness import HarnessRunner
from .registry import agent_registry, skill_registry, tool_registry
from .schemas import WORK_ORDER_SCHEMA, validate_strict
from .utils import read_json, sha256_text, stable_json, utc_now, write_json


class OrchestratorGraph:
    ROUTE: tuple[tuple[str, tuple[str, ...]], ...] = (
        ("specify", ("agent.spec_detallada",)),
        ("clarify", ("agent.spec_detallada",)),
        ("checklist", ("agent.qa_checklist",)),
        ("context", ("agent.context_rag", "agent.ocr_ui_analyst")),
        ("plan", ("agent.architect_plan", "agent.ui_web_modern", "agent.api_security_docs")),
        ("plan_validation", ("agent.security_policy", "agent.qa_checklist")),
        ("tasks", ("agent.architect_plan", "agent.tests_coverage", "agent.doc_tecnica_detalle")),
        ("analyze", ("agent.qa_checklist", "agent.security_policy")),
        ("implement", ("agent.implementacion_doc_code",)),
        ("validate", ("agent.tests_coverage", "agent.security_policy", "agent.qa_checklist")),
        ("observe", ("agent.token_billing", "agent.observability_sre")),
        ("close", ("agent.doc_tecnica_detalle", "agent.token_billing", "agent.qa_checklist")),
    )

    def __init__(self, *, factory_root: Path = ROOT, project_dir: Path) -> None:
        self.factory_root = factory_root
        self.project_dir = project_dir

    def initialize_project(self) -> None:
        from .storage import checked_root
        self.project_dir = checked_root(self.project_dir)
        self.project_dir.mkdir(parents=True, exist_ok=True)
        for rel in ("runs",):
            (self.project_dir / rel).mkdir(parents=True, exist_ok=True)
        aprendizaje = self.project_dir / "Aprendizaje.md"
        if not aprendizaje.exists():
            aprendizaje.write_text("# Aprendizaje\n\nMemoria aislada del proyecto. Sin registros aprobados aun.\n", encoding="utf-8")
        readme = self.project_dir / "README.md"
        if not readme.exists():
            readme.write_text("# Project\n\nCarpeta independiente para el primer proyecto de la fabrica.\n", encoding="utf-8")

    def normalize_work_order(self, objective: str) -> dict[str, Any]:
        work_order = {
            "work_order_id": "WO-" + sha256_text(objective).split(":", 1)[1][:12],
            "objective": objective,
            "work_type": "factory_bootstrap",
            "scope": {
                "include": ["fabrica", "arnes", "agentes", "skills", "tools", "qa", "logs", "project"],
                "exclude": ["deploy", "merge", "db_write", "secret_read", "external_write"],
            },
            "inputs": [
                {"source_id": "SRC-BRIEF-USER", "type": "brief", "authorized": True, "trust": "trusted"},
                {"source_id": "SRC-DOCS-LOCAL", "type": "doc", "path": ".", "authorized": True, "trust": "trusted"},
            ],
            "constraints": {
                "no_web": True,
                "dry_run": True,
                "sandbox_required": True,
                "max_retries": 1,
                "risk": "high",
                "max_cost_usd": 0,
                "max_latency_ms": 300000,
            },
            "expected_outputs": ["project-ready", "agents-registered", "qa-report", "traceability", "final-report"],
            "approval_required_for": ["write", "deploy", "merge", "external_api", "secrets", "infra", "cost_increase", "data_access", "production_data", "db_write"],
        }
        validate_strict(WORK_ORDER_SCHEMA, work_order)
        return work_order

    def run(self, objective: str) -> Path:
        self.initialize_project()
        run_id = "RUN-" + uuid.uuid4().hex
        run_dir = self.project_dir / "runs" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        work_order = self.normalize_work_order(objective)
        write_json(run_dir / "work_order.json", work_order)
        write_json(run_dir / "registries" / "agents.json", {k: v.to_dict() for k, v in agent_registry().items()})
        write_json(run_dir / "registries" / "tools.json", {k: v.__dict__ for k, v in tool_registry().items()})
        write_json(run_dir / "registries" / "skills.json", {k: v.__dict__ for k, v in skill_registry().items()})

        harness = HarnessRunner(factory_root=self.factory_root, project_dir=self.project_dir, run_dir=run_dir)
        results = []
        state: dict[str, Any] = {
            "run_id": run_id,
            "cycle_id": "CYC-000",
            "task_id": "TASK-BOOTSTRAP",
            "phase": "intake",
            "status": "complete",
            "input_hash": sha256_text(stable_json(work_order)),
            "spec_hash": "sha256:TBD-before-spec",
            "policy_version": POLICY_VERSION,
            "tool_registry_version": TOOL_REGISTRY_VERSION,
            "memory_version": MEMORY_VERSION,
            "evidence": [],
            "outputs": {},
            "issues": [],
            "budget": {
                "max_input_tokens": 120000,
                "max_output_tokens": 60000,
                "max_cost_usd": 0,
                "max_latency_ms": 300000,
                "max_tool_calls": 200,
                "used_input_tokens": 0,
                "used_output_tokens": 0,
                "cached_tokens": 0,
                "reasoning_tokens": 0,
                "estimated_cost_usd": 0,
                "tool_calls": 0,
            },
            "approval": {"required": False, "approved": False, "approval_id": "not_required_for_sandbox"},
        }
        harness.obs.event(run_id=run_id, cycle_id="CYC-000", event="run_started", phase="intake", status="complete")

        cycle_index = 1
        for phase, agents in self.ROUTE:
            for agent_id in agents:
                state = {**state, "cycle_id": f"CYC-{cycle_index:03d}", "phase": phase, "task_id": f"TASK-{phase.upper()}-{cycle_index:03d}", "input_hash": sha256_text(stable_json({**work_order, "phase": phase, "agent_id": agent_id}))}
                routing = {
                    "run_id": run_id,
                    "cycle_id": state["cycle_id"],
                    "phase": phase,
                    "selected_agent_id": agent_id,
                    "reason": "ruta SDD controlada; orquestador solo invoca harness.run_agent",
                    "required_gates": agent_registry()[agent_id].gates,
                    "budget": state["budget"],
                    "status": "complete",
                }
                write_json(run_dir / "routing" / f"{state['cycle_id']}.json", routing)
                result = harness.run_agent(agent_id, state)
                results.append(result)
                state["outputs"][agent_id] = result["logs"]["output_hash"]
                state["status"] = result["status"]
                if result["status"] != "complete":
                    write_json(run_dir / "state.json", state)
                    self._finalize(run_dir, run_id, state, results)
                    harness.obs.event(run_id=run_id, cycle_id=state["cycle_id"], event="run_finished", phase=phase, status=state["status"])
                    return run_dir
                cycle_index += 1

        state["status"] = "complete"
        write_json(run_dir / "state.json", state)
        self._finalize(run_dir, run_id, state, results)
        harness.obs.event(run_id=run_id, cycle_id=state["cycle_id"], event="run_finished", phase="close", status=state["status"])
        return run_dir

    def _finalize(self, run_dir: Path, run_id: str, state: dict[str, Any], results: list[dict[str, Any]]) -> None:
        from .reports import finalize_run
        expected = sum(len(agents) for _, agents in self.ROUTE)
        finalize_run(run_dir, state, results, expected_cycles=expected)


def latest_run(project_dir: Path) -> Path | None:
    runs = sorted((project_dir / "runs").glob("RUN-*"), key=lambda path: path.stat().st_mtime, reverse=True)
    return runs[0] if runs else None
