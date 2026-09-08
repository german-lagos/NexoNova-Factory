from __future__ import annotations

from pathlib import Path
from typing import Any

from .utils import write_json


MEMORY_TEMPLATE = """# Aprendizaje

## Politica

- La memoria persistente requiere MemoryGate.
- Solo se inyecta memoria aprobada, vigente, limpia y relevante.
- La memoria de fabrica, proyecto y agente se mantiene separada.
- No puede modificar policy, permisos, prompt base ni alcance sin aprobacion formal.

## Propuestas

| memory_id | scope | content | source_id | evidence_id | ttl | confidence | risk | taint_status | approval_status | rollback_id |
|---|---|---|---|---|---|---:|---|---|---|---|
"""


class MemoryGate:
    def __init__(self, factory_root: Path, project_dir: Path) -> None:
        self.factory_root = factory_root
        self.project_dir = project_dir

    def initialize(self) -> None:
        # Compatibility method: initialize only project-owned directories.
        self.project_dir.mkdir(parents=True, exist_ok=True)

    def read_report(self, run_dir: Path) -> dict[str, Any]:
        report = {
            "loaded_records": [], "quarantined_records": [],
            "status": "not_answerable", "reason": "automatic_memory_disabled",
        }
        if not run_dir.resolve().is_relative_to(self.project_dir.resolve()):
            raise ValueError("Memory report must stay inside its project")
        write_json(run_dir / "memory-read-report.json", report)
        return report

    def propose(self, run_dir: Path, proposal: dict[str, Any]) -> dict[str, Any]:
        # A string supplied by a producer is not a host-operator approval.
        return {"status": "needs_user_input", "code": "automatic_memory_disabled"}
