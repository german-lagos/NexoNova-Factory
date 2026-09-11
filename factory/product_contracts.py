"""P3 preparation contracts. Validation never authorizes or executes generation."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path, PurePosixPath
from .schemas import SchemaError, validate_strict


def obj(properties):
    return {"type": "object", "additionalProperties": False,
            "required": list(properties), "properties": properties}


def enum(*values):
    return {"type": "string", "enum": list(values)}


TEXT = {"type": "string", "minLength": 1, "maxLength": 4096}
SLUG = {"type": "string", "pattern": "[a-z0-9][a-z0-9-]{0,62}"}
HASH = {"type": "string", "pattern": "sha256:[a-f0-9]{64}"}
BOOL = {"type": "boolean"}
STRINGS = {"type": "array", "items": TEXT}

SOURCE_MANIFEST_SCHEMA = obj({
    "format": enum("nexonova.source-manifest.v1"), "source_id": SLUG,
    "tree_hash": HASH, "authorization": TEXT,
    "entries": {"type": "array", "items": obj({
        "path": TEXT, "sha256": HASH, "bytes": {"type": "integer", "minimum": 0},
        "action": enum("KEEP", "ADAPT", "REBUILD", "DROP", "REVIEW"),
        "reason": TEXT, "approval": enum("approved", "pending", "not_selected"),
        "target": {"type": "string"},
    })},
    "missing": STRINGS, "pending_decisions": STRINGS,
})

CORPORATE_SITE_SCHEMA = obj({
    "format": enum("nexonova.corporate-site.v0.1.0"), "project_id": SLUG,
    "locale": enum("es-CL"), "route": enum("/"), "source_id": SLUG,
    "brand": obj({"name": TEXT, "colors": obj({"navy": TEXT, "blue": TEXT, "cyan": TEXT}),
                  "font_family": TEXT, "font_approval": enum("approved", "pending")}),
    "sections": {"type": "array", "items": obj({
        "id": enum("header", "hero", "domains", "about", "plans", "services", "faq", "contact", "footer", "chat", "inquiry"),
        "title": TEXT, "enabled": BOOL,
    })},
    "plans": {"type": "array", "items": obj({
        "id": SLUG, "name": TEXT, "price_clp": {"type": "integer", "minimum": 0},
        "demonstration": enum("provisional"),
    })},
    "services": STRINGS,
    "behaviors": obj({"domains": enum("local-format-only"), "chat": enum("local-scripted"),
                      "inquiry": enum("interest-summary"), "contact": enum("prepare-copy-not-sent"),
                      "persistence": enum("memory-only"), "external_requests": enum("disabled")}),
    "assets": {"type": "array", "items": obj({"path": TEXT, "role": SLUG,
                                                "approval": enum("approved", "pending")})},
    "pending_decisions": STRINGS, "acceptance": STRINGS,
})

PRODUCT_WORK_ORDER_SCHEMA = obj({
    "format": enum("nexonova.product-work-order.v1"), "work_order_id": SLUG,
    "operation": enum("prepare-project"), "client_id": SLUG, "project_id": SLUG,
    "source_id": SLUG, "spec_hash": HASH, "manifest_hash": HASH,
    "authorization": obj({"actor": TEXT, "basis": TEXT,
        "allowed_actions": {"type": "array", "items": enum("snapshot", "validate-contracts")}}),
    "constraints": obj({"source_readonly": enum("required"), "external_services": enum("denied"),
        "max_files": {"type": "integer", "minimum": 1},
        "max_bytes": {"type": "integer", "minimum": 1},
        "generation": enum("not-authorized"), "deployment": enum("denied")}),
})


def digest(value):
    encoded = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return "sha256:" + hashlib.sha256(encoded.encode()).hexdigest()


def relative_path(value):
    path = PurePosixPath(value)
    if not value or path.is_absolute() or "\\" in value or ":" in value or any(x in ("", ".", "..") for x in value.split("/")):
        raise SchemaError("Expected canonical relative path")
    return value


def unique(values, label):
    if len(values) != len(set(values)):
        raise SchemaError("Duplicate " + label)


def tree_digest(entries):
    return digest(sorted(({"path": e["path"], "sha256": e["sha256"], "bytes": e["bytes"]} for e in entries), key=lambda e: e["path"]))


def validate_manifest(value):
    validate_strict(SOURCE_MANIFEST_SCHEMA, value)
    if not value["entries"]:
        raise SchemaError("Empty source snapshot")
    unique([e["path"] for e in value["entries"]], "source path")
    targets = []
    for entry in value["entries"]:
        relative_path(entry["path"])
        if entry["target"]:
            relative_path(entry["target"])
            targets.append(entry["target"])
        if entry["action"] == "REVIEW" and entry["approval"] == "approved":
            raise SchemaError("REVIEW material cannot be approved")
        if entry["action"] == "DROP" and entry["target"]:
            raise SchemaError("Dropped material cannot have a target")
    unique(targets, "target path")
    for path in value["missing"]:
        relative_path(path)
        if path in {e["path"] for e in value["entries"]}:
            raise SchemaError("Missing path is present in snapshot")
    if tree_digest(value["entries"]) != value["tree_hash"]:
        raise SchemaError("Snapshot tree hash mismatch")


def validate_spec(value):
    validate_strict(CORPORATE_SITE_SCHEMA, value)
    unique([s["id"] for s in value["sections"]], "section")
    enabled = {s["id"] for s in value["sections"] if s["enabled"]}
    if not {"header", "hero", "domains", "contact", "footer", "chat", "inquiry"} <= enabled:
        raise SchemaError("Required pilot sections missing")
    unique([p["id"] for p in value["plans"]], "plan")
    unique([a["role"] for a in value["assets"]], "asset role")
    for asset in value["assets"]:
        relative_path(asset["path"])
    if not value["acceptance"] or not value["services"]:
        raise SchemaError("Acceptance and services must be explicit")
    import re
    if any(not re.fullmatch(r"#[a-fA-F0-9]{6}", c) for c in value["brand"]["colors"].values()):
        raise SchemaError("Invalid color token")


def validate_bundle(order, spec, manifest):
    validate_strict(PRODUCT_WORK_ORDER_SCHEMA, order)
    validate_spec(spec)
    validate_manifest(manifest)
    if not order["authorization"]["allowed_actions"]:
        raise SchemaError("Explicit preparation authorization required")
    unique(order["authorization"]["allowed_actions"], "authorized action")
    if order["project_id"] != spec["project_id"] or not order["source_id"] == spec["source_id"] == manifest["source_id"]:
        raise SchemaError("Project/source scope mismatch")
    if digest(spec) != order["spec_hash"] or digest(manifest) != order["manifest_hash"]:
        raise SchemaError("WorkOrder scope changed; authorization must be reviewed")
    limits = order["constraints"]
    if len(manifest["entries"]) > limits["max_files"] or sum(e["bytes"] for e in manifest["entries"]) > limits["max_bytes"]:
        raise SchemaError("Source exceeds authorized inspection budget")
    entries = {e["path"]: e for e in manifest["entries"]}
    for asset in spec["assets"]:
        entry = entries.get(asset["path"])
        if entry is None or entry["action"] == "DROP":
            raise SchemaError("Asset not selected from snapshot")
        if asset["approval"] == "approved" and entry["approval"] != "approved":
            raise SchemaError("Asset approval lacks matching source decision")


def require_material_ready(spec, manifest):
    """A separate gate: a valid preparation bundle is NOT release approval."""
    validate_spec(spec)
    validate_manifest(manifest)
    if spec["pending_decisions"] or manifest["pending_decisions"] or spec["brand"]["font_approval"] != "approved":
        raise SchemaError("Human material decisions pending")
    entries = {e["path"]: e for e in manifest["entries"]}
    for asset in spec["assets"]:
        e = entries.get(asset["path"])
        if not e or asset["approval"] != "approved" or e["approval"] != "approved" or not e["target"] or e["action"] not in {"KEEP", "ADAPT"}:
            raise SchemaError("Unapproved material cannot enter a product")


def verify_source(root: Path, manifest):
    """Read-only verification against an explicitly supplied root; no imports or scripts."""
    validate_manifest(manifest)
    root = root.absolute()
    if not root.is_dir() or any(p.is_symlink() for p in (root, *root.parents)):
        raise SchemaError("Invalid source root")
    paths = []
    for path in root.rglob("*"):
        if path.is_symlink():
            raise SchemaError("Source links are unsupported")
        if path.is_file():
            paths.append(path.relative_to(root).as_posix())
        elif not path.is_dir():
            raise SchemaError("Special source file unsupported")
    if set(paths) != {e["path"] for e in manifest["entries"]}:
        raise SchemaError("Snapshot file inventory changed")
    for entry in manifest["entries"]:
        path = root / entry["path"]
        if path.name.startswith(".env") or path.suffix in {".key", ".pem", ".p12", ".pfx"}:
            raise SchemaError("Sensitive source requires separate handling")
        if path.stat().st_nlink != 1:
            raise SchemaError("Source hardlinks unsupported")
        if path.stat().st_size != entry["bytes"] or "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            raise SchemaError("Source bytes changed")
    return manifest["tree_hash"]
