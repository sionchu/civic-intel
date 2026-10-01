"""Executable dependency and retired-path contract, without loading runtime databases."""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path


def check(root: Path) -> list[str]:
    failures = []
    rules = {
        "packages/domain": (
            "sqlalchemy",
            "fastapi",
            "packages.persistence",
            "packages.application",
            "apps",
            "workers",
        ),
        "packages/application": (
            "sqlalchemy",
            "fastapi",
            "packages.persistence",
            "packages.connectors",
            "apps",
            "workers",
        ),
    }
    for folder, forbidden in rules.items():
        for path in (root / folder).rglob("*.py"):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if not isinstance(node, (ast.Import, ast.ImportFrom)):
                    continue
                imports = (
                    [node.module or ""]
                    if isinstance(node, ast.ImportFrom)
                    else [item.name for item in node.names]
                    if isinstance(node, ast.Import)
                    else []
                )
                for name in imports:
                    if any(name == prefix or name.startswith(prefix + ".") for prefix in forbidden):
                        failures.append(
                            f"{path.relative_to(root)}:{node.lineno}: forbidden dependency {name}"
                        )
    for obsolete in (
        "packages/domain/db.py",
        "packages/persistence/repository.py",
        "workers/sync.py",
    ):
        if (root / obsolete).exists():
            failures.append(f"retired path remains: {obsolete}")
    scripts = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"][
        "scripts"
    ]
    if set(scripts) != {"civic", "civic-quality"}:
        failures.append("console scripts must use the canonical civic command boundary")
    operational_modules = {
        "operator_console": "SCHEMA_OR_DEPLOY",
        "alio_cross_lane_identity_candidates": "READ_ONLY",
        "gukgam_schedule_probe": "READ_ONLY",
        "public_beta_preflight": "READ_ONLY",
    }
    for path in (root / "workers").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if any(isinstance(node, ast.FunctionDef) and node.name == "main" for node in tree.body):
            effect = next(
                (
                    node.value.value
                    for node in tree.body
                    if isinstance(node, ast.Assign)
                    and any(
                        isinstance(target, ast.Name) and target.id == "COMMAND_EFFECT"
                        for target in node.targets
                    )
                    and isinstance(node.value, ast.Constant)
                ),
                None,
            )
            if effect != operational_modules.get(path.stem) or effect is None:
                failures.append(f"unclassified standalone operation: {path.name}")
    # Current continuation headings are unique; history belongs in linked archives.
    for name in ("HANDOFF.md", "docs/exec-plans/active/architecture-current-master.md"):
        path = root / name
        if path.exists():
            headings = [
                line
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.startswith("## ")
            ]
            if len(headings) != len(set(headings)):
                failures.append(f"duplicate current continuation section: {name}")
    return failures


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    failures = check(root)
    for failure in failures:
        print(failure)
    if not failures:
        print("architecture-contract=PASS")
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
