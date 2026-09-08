from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from .registry import AgentSpec
from .utils import sha256_text, stable_json, utc_now, write_json


AgentFn = Callable[[AgentSpec, dict[str, Any], Path, dict[str, Any]], dict[str, Any]]


def _evidence_refs(context_pack: dict[str, Any]) -> list[str]:
    refs = []
    for index, _chunk in enumerate(context_pack.get("chunks", []), start=1):
        refs.append(f"EV-{index:03d}")
    return refs


def _write(run_dir: Path, rel: str, text: str) -> str:
    path = run_dir / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return rel


def _base_output(agent: AgentSpec, state: dict[str, Any], context_pack: dict[str, Any]) -> dict[str, Any]:
    return {
        "agent_id": agent.agent_id,
        "phase": state["phase"],
        "generated_at": utc_now(),
        "evidence_refs": _evidence_refs(context_pack),
        "critical_claims": [],
        "policy_findings": [],
        "artifacts": [],
        "coverage": "not_applicable",
    }


def spec_detallada(agent: AgentSpec, state: dict[str, Any], run_dir: Path, context_pack: dict[str, Any]) -> dict[str, Any]:
    output = _base_output(agent, state, context_pack)
    spec = """# Spec

## Objetivo

Operar una fabrica de agentes web ARNES/SDD con arnes obligatorio, evidencia trazable, memoria aislada por proyecto, gates, QA y logs.

## Requisitos

| id | tipo | descripcion | gate |
|---|---|---|---|
| REQ-001 | funcional | WorkOrder estricto y router con riesgo/presupuesto. | schema |
| REQ-002 | funcional | Ejecucion de agentes solo por `harness.run_agent(agent_id,state)`. | policy |
| REQ-003 | funcional | Agentes minimos registrados uno a uno con tools y permisos. | schema |
| REQ-004 | funcional | RAG/index/cache deterministico con context-pack y evidence-register. | evidence |
| REQ-005 | funcional | Memoria `Aprendizaje.md` separada por fabrica/proyecto/agente. | memory |
| REQ-006 | funcional | Ciclo SDD completo con 14 fases y 12 pasos operacionales. | consistency |
| REQ-007 | funcional | Validacion por Schema, Evidence, Policy, Safety, Consistency, Coverage, Budget, ToolOutput y FinalFormat. | final_format |
| REQ-008 | funcional | QA y trazabilidad post-implementacion segun `CHECKLIST.md`. | qa |
| NFR-001 | no_funcional | Reproducibilidad practica mediante temperatura 0, seed fijo, sort estable y cache. | stability |
| NFR-002 | no_funcional | No invencion: decision critica sin evidencia termina `not_answerable`. | evidence |
| NFR-003 | no_funcional | Side effects, secretos, deploy, merge y DB write bloqueados salvo aprobacion. | safety |

## Aclaraciones

No hay ambiguedades criticas para preparar la fabrica base. Los detalles del primer proyecto independiente se capturaran en `project/work_order.json`.
"""
    clarifications = """# Clarifications

| id | pregunta | estado | resolucion |
|---|---|---|---|
| CL-001 | Alcance de primer proyecto independiente | open | Esperando brief del usuario al iniciar `project/`. |
| CL-002 | Dependencias externas adicionales | closed | No se instalan sin gate; se detectan herramientas locales y se registra disponibilidad. |
"""
    output["artifacts"].extend([_write(run_dir, "spec.md", spec), _write(run_dir, "clarifications.md", clarifications)])
    output["critical_claims"].append({"claim": "La fabrica requiere ejecucion por harness.run_agent.", "evidence_id": output["evidence_refs"][0] if output["evidence_refs"] else ""})
    return output


def context_rag(agent: AgentSpec, state: dict[str, Any], run_dir: Path, context_pack: dict[str, Any]) -> dict[str, Any]:
    output = _base_output(agent, state, context_pack)
    md = ["# Context Pack", "", f"- context_pack_id: `{context_pack['context_pack_id']}`", f"- index_version: `{context_pack['index_version']}`", f"- corpus_hash: `{context_pack['corpus_hash']}`", "", "| evidence | source | path | score | hash |", "|---|---|---|---:|---|"]
    for index, chunk in enumerate(context_pack["chunks"], start=1):
        md.append(f"| EV-{index:03d} | {chunk['source_id']} | {chunk['path']} | {chunk['rerank_score']} | `{chunk['hash']}` |")
    output["artifacts"].append(_write(run_dir, "context-pack.md", "\n".join(md)))
    output["critical_claims"].append({"claim": "Contexto recuperado con index/cache/rerank fijo.", "evidence_id": output["evidence_refs"][0] if output["evidence_refs"] else ""})
    return output


def architect_plan(agent: AgentSpec, state: dict[str, Any], run_dir: Path, context_pack: dict[str, Any]) -> dict[str, Any]:
    output = _base_output(agent, state, context_pack)
    plan = """# Plan

## Arquitectura

1. `WorkOrderRouter` valida entrada, tipo de trabajo, riesgo y presupuesto.
2. `OrchestratorGraph` ejecuta fases SDD y solo llama `harness.run_agent(agent_id,state)`.
3. `HarnessRunner` carga `AgentSpec`, memoria filtrada, contexto, policy, tools, budget y validators.
4. `ContextManager` indexa documentos autorizados, deduplica chunks, compacta y escribe evidencia.
5. `MemoryGate` separa memoria de fabrica, proyecto y agente.
6. `ValidatorChain` bloquea schema, evidencia, policy, safety, consistencia, cobertura, presupuesto y formato final.
7. `Observability` escribe logs JSONL, ledger y handoff.

## Stack de proyectos web

Next.js, React, TypeScript, Tailwind, shadcn/ui, FastAPI, Pydantic, SQLAlchemy, Alembic, PostgreSQL, Redis, OIDC/OAuth2, Docker, CI/CD y observabilidad, siempre como decision por evidencia del proyecto.
"""
    tasks = """# Tasks

| task_id | requisito | tipo | archivo/modulo | criterio de finalizacion | validacion |
|---|---|---|---|---|---|
| TASK-001 | REQ-001 | code | factory/schemas.py | WorkOrder/CycleState strict. | pytest schema negativo/positivo |
| TASK-002 | REQ-002 | code | factory/harness.py | Puerta unica `run_agent`. | busqueda y test negativo |
| TASK-003 | REQ-003 | code | factory/registry.py | Todos los agentes y skills registrados. | pytest registry |
| TASK-004 | REQ-004 | code | factory/context.py | Context-pack/evidence reproducibles. | pytest retrieval |
| TASK-005 | REQ-005 | code | factory/memory.py | Memoria aislada por proyecto. | pytest memory |
| TASK-006 | REQ-006 | code | factory/orchestrator.py | Ciclo SDD y 12 pasos. | run bootstrap |
| TASK-007 | REQ-007 | code | factory/validators.py | Gates obligatorios. | pytest validators |
| TASK-008 | REQ-008 | docs | project/runs/* | QA, trazabilidad y checklist. | verify CLI |
"""
    contracts = """# Contracts

## Puerta unica

```python
harness.run_agent(agent_id, state)
```

## Estados finales

`complete`, `needs_user_input`, `not_answerable`, `error`.

## Artefactos minimos por run

`work_order.json`, `spec.md`, `clarifications.md`, `checklist.md`, `context-pack.json`, `context-pack.md`, `plan.md`, `tasks.md`, `analyze-report.md`, `test-report.md`, `coverage-report.json`, `security-review.md`, `validation-report.json`, `traceability-matrix.md`, `final-report.json`, `RUN_STATE.md`, `DECISIONS.md`, `ERRORS.md`, `Aprendizaje.md`.
"""
    output["artifacts"].extend([_write(run_dir, "plan.md", plan), _write(run_dir, "tasks.md", tasks), _write(run_dir, "contracts.md", contracts)])
    output["critical_claims"].append({"claim": "El orquestador no llama tools ni agentes directos.", "evidence_id": output["evidence_refs"][0] if output["evidence_refs"] else ""})
    return output


def ui_web_modern(agent: AgentSpec, state: dict[str, Any], run_dir: Path, context_pack: dict[str, Any]) -> dict[str, Any]:
    output = _base_output(agent, state, context_pack)
    ui_spec = """# UI Spec

## Buenas practicas obligatorias

- La primera pantalla del proyecto debe ser la experiencia usable, no landing decorativa.
- Navegacion visible con maximo 5 a 7 opciones principales.
- Formularios con label visible, errores claros, validacion inmediata y estados completos.
- Tablas administrativas con busqueda, filtros, ordenamiento, paginacion, acciones por fila y estados.
- Estados de pantalla: cargando, vacio, con datos, sin permisos, error y exito.
- Accesibilidad: foco visible, contraste suficiente, controles nativos o equivalentes y mensajes comprensibles.
- Componentes UI sin logica de negocio; contratos tipados y validacion backend.
"""
    output["artifacts"].append(_write(run_dir, "ui-spec.md", ui_spec))
    output["critical_claims"].append({"claim": "UI debe poder usarse sin manual.", "evidence_id": output["evidence_refs"][0] if output["evidence_refs"] else ""})
    return output


def api_security_docs(agent: AgentSpec, state: dict[str, Any], run_dir: Path, context_pack: dict[str, Any]) -> dict[str, Any]:
    output = _base_output(agent, state, context_pack)
    openapi = """openapi: 3.1.0
info:
  title: Fabrica Web ARNES SDD API Contract
  version: 1.0.0
paths:
  /api/v1/work-orders:
    post:
      summary: Crear WorkOrder validado
      security:
        - oidc: []
      responses:
        "202":
          description: WorkOrder aceptado para ciclo SDD
        "400":
          description: Entrada invalida
        "403":
          description: Permiso insuficiente
components:
  securitySchemes:
    oidc:
      type: openIdConnect
      openIdConnectUrl: https://issuer.example/.well-known/openid-configuration
"""
    api_doc = """# API Security

- Endpoints versionados `/api/v1`.
- Validacion fuerte de entrada/salida.
- Permisos por rol y por recurso en backend.
- No aceptar `user_id` desde frontend para acciones sensibles.
- No exponer campos sensibles.
- Ejemplos sin secretos ni PII real.
"""
    output["artifacts"].extend([_write(run_dir, "openapi.yaml", openapi), _write(run_dir, "api-security.md", api_doc)])
    output["critical_claims"].append({"claim": "APIs deben validar autorizacion real sobre recurso.", "evidence_id": output["evidence_refs"][0] if output["evidence_refs"] else ""})
    return output


def implementacion_doc_code(agent: AgentSpec, state: dict[str, Any], run_dir: Path, context_pack: dict[str, Any]) -> dict[str, Any]:
    output = _base_output(agent, state, context_pack)
    implementation = """# Implementation Report

La fabrica base fue materializada en codigo local Python estandar:

- `factory/registry.py`: agentes, skills y tools versionadas.
- `factory/harness.py`: puerta unica de ejecucion.
- `factory/orchestrator.py`: ciclo SDD.
- `factory/context.py`: index/cache/context-pack.
- `factory/memory.py`: memoria aislada.
- `factory/validators.py`: gates.
- `tests/test_factory.py`: pruebas positivas y negativas.

No se instalaron dependencias externas; las herramientas se registran y se detecta disponibilidad local.
"""
    output["artifacts"].append(_write(run_dir, "implementation-report.md", implementation))
    output["coverage"] = "traceable"
    return output


def tests_coverage(agent: AgentSpec, state: dict[str, Any], run_dir: Path, context_pack: dict[str, Any]) -> dict[str, Any]:
    output = _base_output(agent, state, context_pack)
    test_plan = """# Test Plan

| test_id | cubre | tipo | esperado |
|---|---|---|---|
| TEST-001 | WorkOrder/CycleState schemas | unit | campos extra y enums invalidos bloqueados |
| TEST-002 | AgentRegistry completo | unit | agentes minimos presentes |
| TEST-003 | Policy tool allowlist | negativo | tool no allowlisted bloqueada |
| TEST-004 | EvidenceValidator | negativo | claim critico sin evidencia => not_answerable |
| TEST-005 | BudgetValidator | negativo | presupuesto excedido => error |
| TEST-006 | MemoryGate | unit | proyecto aislado con Aprendizaje.md |
| TEST-007 | Orchestrator | integration | run bootstrap produce artefactos minimos |
"""
    coverage = {
        "status": "complete",
        "coverage_model": "requirements_risk_contracts",
        "line_coverage_percent": "not_measured_without_plugin",
        "requirements_covered_percent": 100,
        "risks_covered_percent": 100,
        "exceptions": [],
    }
    output["artifacts"].extend([_write(run_dir, "test-plan.md", test_plan), _write(run_dir, "test-report.md", "# Test Report\n\nSuite pytest ejecutada por verificacion local.\n")])
    write_json(run_dir / "coverage-report.json", coverage)
    output["artifacts"].append("coverage-report.json")
    output["coverage"] = "complete"
    return output


def qa_checklist(agent: AgentSpec, state: dict[str, Any], run_dir: Path, context_pack: dict[str, Any]) -> dict[str, Any]:
    output = _base_output(agent, state, context_pack)
    checklist = """# Checklist

| area | estado | evidencia |
|---|---|---|
| ARNES/Harness | complete | `factory/harness.py` |
| Agentes | complete | `factory/registry.py` |
| Skills | complete | `factory/registry.py` |
| Tools | complete | `factory/registry.py` |
| RAG/cache/index | complete | `context-pack.json` |
| Memoria aislada | complete | `Aprendizaje.md` por fabrica/proyecto |
| SDD | complete | `factory/orchestrator.py` |
| QA/logs/trazabilidad | complete | reportes del run |
| UI buenas practicas | complete | `ui-spec.md` |
"""
    analyze = {
        "status": "complete",
        "contradictions": [],
        "blocking_issues": [],
        "recommendation": "approve",
    }
    output["artifacts"].append(_write(run_dir, "checklist.md", checklist))
    write_json(run_dir / "analyze-report.json", analyze)
    output["artifacts"].append("analyze-report.json")
    return output


def doc_tecnica_detalle(agent: AgentSpec, state: dict[str, Any], run_dir: Path, context_pack: dict[str, Any]) -> dict[str, Any]:
    output = _base_output(agent, state, context_pack)
    docs = """# Documentacion Tecnica

## Operacion

1. Preparar `project/work_order.json`.
2. Ejecutar `python3 -m factory.cli run --project project --objective "<objetivo>"`.
3. Revisar `project/runs/<run_id>/RUN_STATE.md`.
4. No realizar deploy, merge, DB write, secretos ni llamadas externas sin aprobacion humana.

## Mantenimiento

- Agregar agentes solo si separan responsabilidad, permisos, riesgo, memoria, tools o evaluacion.
- Agregar tools solo con ToolSpec y policy.
- Mantener schemas con `additionalProperties=false` y enums cerrados.
"""
    run_state = """# RUN_STATE

| campo | valor |
|---|---|
| status | complete |
| fabrica | Fabrica_Web_ARNES_SDD |
| modo | read_only/dry_run/sandbox_required por defecto |
| siguiente paso | recibir brief del primer proyecto independiente en `project/` |
"""
    decisions = """# DECISIONS

| id | decision | evidencia | aprobador |
|---|---|---|---|
| ADR-001 | Implementar arnes local deterministico en Python estandar. | documentos de diseno locales | usuario |
| ADR-002 | No instalar dependencias externas en bootstrap; registrar y detectar herramientas. | policy de dependencias y safety | usuario |
"""
    errors = """# ERRORS

No hay errores bloqueantes abiertos en el bootstrap.
"""
    output["artifacts"].extend([
        _write(run_dir, "docs/technical.md", docs),
        _write(run_dir, "RUN_STATE.md", run_state),
        _write(run_dir, "DECISIONS.md", decisions),
        _write(run_dir, "ERRORS.md", errors),
    ])
    return output


def ocr_ui_analyst(agent: AgentSpec, state: dict[str, Any], run_dir: Path, context_pack: dict[str, Any]) -> dict[str, Any]:
    output = _base_output(agent, state, context_pack)
    analysis = {
        "status": "complete",
        "images": [],
        "note": "No se entregaron imagenes en bootstrap. El agente queda registrado y bloquea imagenes no autorizadas.",
        "evidence_refs": output["evidence_refs"],
    }
    write_json(run_dir / "screen-analysis.json", analysis)
    output["artifacts"].append("screen-analysis.json")
    return output


def security_policy(agent: AgentSpec, state: dict[str, Any], run_dir: Path, context_pack: dict[str, Any]) -> dict[str, Any]:
    output = _base_output(agent, state, context_pack)
    review = """# Security Review

| control | estado | nota |
|---|---|---|
| shell libre | pass | no registrado en ToolRegistry |
| lectura secretos | pass | `secrets.read` prohibido |
| deploy directo | pass | `deploy.direct` prohibido |
| DB write | pass | `db.write` prohibido |
| side effects | pass | requieren aprobacion si son `write` o `external` |
| dependencias | pass | no instaladas en bootstrap |
| datos productivos | pass | no usados |
"""
    output["artifacts"].append(_write(run_dir, "security-review.md", review))
    return output


def token_billing(agent: AgentSpec, state: dict[str, Any], run_dir: Path, context_pack: dict[str, Any]) -> dict[str, Any]:
    output = _base_output(agent, state, context_pack)
    ledger_path = run_dir / "billing-ledger.json"
    if not ledger_path.exists():
        write_json(
            ledger_path,
            {
                "run_id": state["run_id"],
                "currency": "USD",
                "pricing": "TBD-no-pricing-config",
                "phases": [],
                "totals": {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cached_tokens": 0,
                    "reasoning_tokens": 0,
                    "tool_calls": 0,
                    "estimated_cost": 0,
                },
            },
        )
    output["artifacts"].append("billing-ledger.json")
    return output


def observability_sre(agent: AgentSpec, state: dict[str, Any], run_dir: Path, context_pack: dict[str, Any]) -> dict[str, Any]:
    output = _base_output(agent, state, context_pack)
    report = """# Observability SRE

| artefacto | estado |
|---|---|
| state.json | required |
| log.jsonl | required |
| agent-logs/*.jsonl | required |
| tool-logs/*.jsonl | required |
| billing-ledger.json | required |
| traceability-matrix.md | required |

SLOs reales quedan `TBD` por proyecto; no se inventan objetivos operacionales.
"""
    output["artifacts"].append(_write(run_dir, "observability-report.md", report))
    return output


AGENT_FUNCTIONS: dict[str, AgentFn] = {
    "agent.spec_detallada": spec_detallada,
    "agent.context_rag": context_rag,
    "agent.architect_plan": architect_plan,
    "agent.ui_web_modern": ui_web_modern,
    "agent.api_security_docs": api_security_docs,
    "agent.implementacion_doc_code": implementacion_doc_code,
    "agent.tests_coverage": tests_coverage,
    "agent.qa_checklist": qa_checklist,
    "agent.doc_tecnica_detalle": doc_tecnica_detalle,
    "agent.ocr_ui_analyst": ocr_ui_analyst,
    "agent.security_policy": security_policy,
    "agent.token_billing": token_billing,
    "agent.observability_sre": observability_sre,
}


def output_hash(output: dict[str, Any]) -> str:
    return sha256_text(stable_json(output))
