"""Read-only structural/import/legacy checks. Does not certify product readiness."""
from __future__ import annotations

import ast
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def validate() -> list[str]:
    issues = []
    for path in sorted((ROOT / "factory").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        module = importlib.import_module("factory" if path.stem == "__init__" else "factory." + path.stem)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.level:
                name = importlib.util.resolve_name("." * node.level + (node.module or ""), module.__package__)
                imported = importlib.import_module(name)
                for alias in node.names:
                    if alias.name != "*" and not hasattr(imported, alias.name):
                        issues.append(f"Unresolved import: {path.name}:{node.lineno}: {name}.{alias.name}")
    for path in (ROOT / "tests").glob("*.py"):
        ast.parse(path.read_text(), filename=str(path))
    baseline = json.loads((ROOT / "docs/migration/baseline-sha256.json").read_text())
    protected = ("AGENTS.md", "CURRENT_ARCHITECTURE.md", "TARGET_ARCHITECTURE.md", "MIGRATION_PLAN.md")
    for name, digest in baseline.items():
        if name.startswith("project/") or name in protected:
            path = ROOT / name
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                issues.append("Preserved artifact changed: " + name)
    for path in [ROOT / "README.md", ROOT / "REFACTOR_REPORT.md", *(ROOT / "docs").rglob("*.md")]:
        if not path.is_file():
            issues.append("Missing document: " + str(path.relative_to(ROOT)))
            continue
        for target in re.findall(r"\]\(([^)]+)\)", path.read_text()):
            if re.match(r"[a-z]+://", target) or target.startswith("#"):
                continue
            target = target.split("#", 1)[0]
            if not (path.parent / target).exists():
                issues.append(f"Broken document link: {path.relative_to(ROOT)} -> {target}")
    from factory import __version__
    from factory.constants import FACTORY_VERSION
    import tomllib
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text())
    if not __version__ == FACTORY_VERSION == metadata["project"]["version"]:
        issues.append("Package version mismatch")
    from factory.config import FactoryConfig
    FactoryConfig.load(ROOT / "config/factory.json")
    return issues


if __name__ == "__main__":
    problems = validate()
    for problem in problems:
        print(problem)
    print("structural_validation=" + ("error" if problems else "complete"))
    raise SystemExit(bool(problems))
