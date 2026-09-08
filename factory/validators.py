from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .constants import FINAL_STATUSES
from .utils import read_json, sha256_text
from .schemas import AGENT_RESULT_SCHEMA, CYCLE_STATE_SCHEMA, SchemaError, validate_strict


@dataclass(frozen=True)
class ValidationItem:
    validator: str
    status: str
    code: str
    message: str


class ValidatorChain:
    order = (
        "SchemaValidator",
        "EvidenceValidator",
        "PolicyValidator",
        "SafetyValidator",
        "ConsistencyValidator",
        "CoverageValidator",
        "BudgetValidator",
        "ToolOutputValidator",
        "FinalFormatValidator",
    )
    stop_on = {
        "policy_denied",
        "missing_critical_evidence",
        "unsafe_action",
        "budget_exceeded",
        "schema_unrecoverable",
    }

    def validate_state(self, state: dict[str, Any]) -> list[ValidationItem]:
        try:
            validate_strict(CYCLE_STATE_SCHEMA, state)
        except SchemaError as exc:
            return [ValidationItem("SchemaValidator", "error", "schema_unrecoverable", str(exc))]
        return [ValidationItem("SchemaValidator", "complete", "schema_valid", "CycleState valido.")]

    def validate_agent_result(self, result: dict[str, Any]) -> list[ValidationItem]:
        try:
            validate_strict(AGENT_RESULT_SCHEMA, result)
        except SchemaError as exc:
            return [ValidationItem("SchemaValidator", "error", "schema_unrecoverable", str(exc))]
        return [ValidationItem("SchemaValidator", "complete", "schema_valid", "AgentResult valido.")]

    def validate_output(
        self,
        *,
        state: dict[str, Any],
        output: dict[str, Any],
        required_gates: tuple[str, ...],
        run_dir: Path,
    ) -> list[ValidationItem]:
        items: list[ValidationItem] = []
        items.extend(self.validate_state(state))
        if any(item.code in self.stop_on for item in items):
            return items

        evidence_refs = output.get("evidence_refs", [])
        critical_claims = output.get("critical_claims", [])
        try:
            if not isinstance(evidence_refs, list) or not all(isinstance(x, str) and x for x in evidence_refs):
                raise ValueError("Invalid evidence references")
            if not isinstance(critical_claims, list) or any(not isinstance(c, dict) or not c.get("evidence_id") or c["evidence_id"] not in evidence_refs for c in critical_claims):
                raise ValueError("Claim without a resolvable evidence reference")
            if evidence_refs:
                records = read_json(run_dir / "evidence-register.json")["records"]
                chunks = read_json(run_dir / "context-pack.json")["chunks"]
                by_id = {r["evidence_id"]: r for r in records}
                by_chunk = {c["chunk_id"]: c for c in chunks}
                if len(by_id) != len(records):
                    raise ValueError("Duplicate evidence IDs")
                for ref in evidence_refs:
                    record = by_id[ref]
                    chunk = by_chunk[record["chunk_id"]]
                    if record["source_id"] != chunk["source_id"] or record["hash"] != chunk["hash"] or chunk["hash"] != sha256_text(chunk["content"]):
                        raise ValueError("Evidence content/source mismatch")
            items.append(ValidationItem("EvidenceValidator", "complete", "evidence_valid", "Snapshot references and consumed-content hashes checked; semantic review is separate."))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            items.append(ValidationItem("EvidenceValidator", "not_answerable", "missing_critical_evidence", str(exc)))

        policy_codes = output.get("policy_findings", [])
        if any(code in {"policy_denied", "secret_detected", "unsafe_action"} for code in policy_codes):
            items.append(ValidationItem("PolicyValidator", "error", "policy_denied", "Policy finding bloqueante."))
        else:
            items.append(ValidationItem("PolicyValidator", "complete", "policy_valid", "Policy sin bloqueos."))

        unsafe_markers = ("BEGIN RSA PRIVATE KEY", "OPENAI_API_KEY", "password=", "Authorization: Bearer")
        serialized = str(output)
        if any(marker in serialized for marker in unsafe_markers):
            items.append(ValidationItem("SafetyValidator", "error", "unsafe_action", "Posible secreto detectado."))
        else:
            items.append(ValidationItem("SafetyValidator", "complete", "safety_valid", "Sin secretos obvios ni acciones inseguras."))

        # Never accept assertions from the producer as independent quality evidence.
        unsupported = set(required_gates) - {"schema", "evidence", "budget"}
        for gate in sorted(unsupported):
            items.append(ValidationItem("RequiredGateValidator", "error", "gate_not_implemented", f"Required gate has no executable verifier: {gate}"))

        budget = state["budget"]
        limits = (("tool_calls", "max_tool_calls"), ("estimated_cost_usd", "max_cost_usd"),
                  ("used_input_tokens", "max_input_tokens"), ("used_output_tokens", "max_output_tokens"))
        exceeded = any(budget[used] < 0 or budget[limit] < 0 or budget[used] > budget[limit] for used, limit in limits)
        if exceeded:
            items.append(ValidationItem("BudgetValidator", "error", "budget_exceeded", "Presupuesto excedido."))
        else:
            items.append(ValidationItem("BudgetValidator", "complete", "budget_valid", "Declared numeric budgets checked; runtime timing is an executor responsibility."))

        return items

    @staticmethod
    def status_from_items(items: list[ValidationItem]) -> str:
        for item in items:
            if item.status in FINAL_STATUSES and item.status != "complete":
                return item.status
        return "complete"

    @staticmethod
    def as_report(items: list[ValidationItem]) -> dict[str, Any]:
        return {
            "status": ValidatorChain.status_from_items(items),
            "items": [item.__dict__ for item in items],
        }
