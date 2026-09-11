from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from .constants import ROOT
from .orchestrator import OrchestratorGraph, latest_run
from .registry import agent_registry, tool_registry
from .utils import read_json, write_json
from .reports import verify_run
from .storage import ProjectStore
from .config import FactoryConfig
from .executor import TOOL_COMMANDS, ToolExecutor, redact


def _project(path: str) -> Path:
    return Path(path).absolute()


def cmd_init_project(args: argparse.Namespace) -> int:
    project_dir = _project(args.project)
    OrchestratorGraph(factory_root=ROOT, project_dir=project_dir).initialize_project()
    write_json(project_dir / "tool-availability.json", detect_tools())
    print(f"legacy_workspace_initialized={project_dir}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    project_dir = _project(args.project)
    run_dir = OrchestratorGraph(factory_root=ROOT, project_dir=project_dir).run(args.objective)
    write_json(project_dir / "latest-run.json", {"run_dir": str(run_dir.relative_to(project_dir))})
    print(f"run_dir={run_dir}")
    return 0 if read_json(run_dir / "final-report.json")["status"] == "complete" else 1


def cmd_verify(args: argparse.Namespace) -> int:
    project_dir = _project(args.project)
    run_dir = Path(args.run).resolve() if args.run else latest_run(project_dir)
    if run_dir is None:
        print("error=no_run_found")
        return 2
    result = verify_run(run_dir)
    print(f"status={result['status']}")
    print(f"run_dir={run_dir}")
    if result["missing"]:
        print("missing=" + ",".join(result["missing"]))
    return 0 if result["status"] == "complete" else 1


def cmd_list(args: argparse.Namespace) -> int:
    payload: dict[str, Any] = {
        "agents": sorted(agent_registry()),
        "tools": sorted(tool_registry()),
        "catalog_status": "legacy_not_executable",
        "experimental_adapters": sorted(TOOL_COMMANDS),
    }
    write_json(Path(args.output).resolve(), payload) if args.output else print(payload)
    return 0


def detect_tools() -> dict[str, Any]:
    detected = {}
    for tool_id, spec in tool_registry().items():
        if spec.available_command:
            detected[tool_id] = {
                "command": spec.available_command,
                "available": False,
                "command_present": shutil.which(spec.available_command) is not None,
                "reason": "No executable adapter registered",
            }
        else:
            detected[tool_id] = {"command": None, "available": False, "reason": "Declarative capability only"}
    return detected


def cmd_workspace(args: argparse.Namespace) -> int:
    store = ProjectStore(Path(args.root), args.client, args.project_id)
    if args.command == "init-workspace":
        store.initialize()
        print(f"workspace={store.workspace}")
        return 0
    config = FactoryConfig.load(Path(args.config)) if args.config else FactoryConfig()
    if args.command == "approve-tool":
        if config.python_image is None:
            raise ValueError("Choose and review a pinned Python image before approving execution")
        executor = ToolExecutor(store, config, work_order=read_json(Path(args.work_order)) if args.work_order else None)
        print("approval_id=" + store.approve_tool(args.tool, actor=args.actor, policy_hash=executor.policy_hash))
        return 0
    result = ToolExecutor(store, config, work_order=read_json(Path(args.work_order)) if args.work_order else None).run(args.tool, approval_id=args.approval, dry_run=args.dry_run)
    print(json.dumps(result, ensure_ascii=True))
    return 0 if result["status"] == "complete" else 1


def cmd_state(args: argparse.Namespace) -> int:
    from .state_transfer import import_reference, recover_run
    store = ProjectStore(Path(args.root), args.client, args.project_id)
    if args.command == "import-legacy-reference":
        print("reference=" + import_reference(store, Path(args.source)))
        return 0
    result = recover_run(store, args.run_id)
    print(json.dumps(result))
    return 0 if result["status"] == "complete" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="NexoNova Factory — núcleo local; bootstrap legado bloqueado")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init-project")
    init.add_argument("--project", default="project")
    init.set_defaults(func=cmd_init_project)

    run = sub.add_parser("run")
    run.add_argument("--project", default="project")
    run.add_argument("--objective", required=True)
    run.set_defaults(func=cmd_run)

    verify = sub.add_parser("verify")
    verify.add_argument("--project", default="project")
    verify.add_argument("--run")
    verify.set_defaults(func=cmd_verify)

    list_cmd = sub.add_parser("list")
    list_cmd.add_argument("--output")
    list_cmd.set_defaults(func=cmd_list)

    for command in ("init-workspace", "approve-tool", "run-tool"):
        item = sub.add_parser(command)
        item.add_argument("--root", required=True, help="Dedicated private root outside the factory checkout")
        item.add_argument("--client", required=True)
        item.add_argument("--project-id", required=True)
        if command != "init-workspace":
            item.add_argument("--tool", choices=sorted(TOOL_COMMANDS), required=True)
            item.add_argument("--work-order", help="Optional restrictive test WorkOrder JSON")
        if command == "approve-tool":
            item.add_argument("--config")
            item.add_argument("--actor", required=True, help="Host operator issuing this scoped, one-use approval")
        if command == "run-tool":
            item.add_argument("--config")
            item.add_argument("--approval")
            item.add_argument("--dry-run", action="store_true")
        item.set_defaults(func=cmd_workspace)
    for command in ("import-legacy-reference", "recover-run"):
        item = sub.add_parser(command)
        item.add_argument("--root", required=True)
        item.add_argument("--client", required=True)
        item.add_argument("--project-id", required=True)
        if command == "import-legacy-reference":
            item.add_argument("--source", required=True)
        else:
            item.add_argument("--run-id", required=True)
        item.set_defaults(func=cmd_state)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("interrupted=SIGINT", file=sys.stderr)
        return 130
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print("error=" + redact(str(exc)), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
