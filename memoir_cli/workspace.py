"""C1 — the workspace data model. Shared by every adapter."""

from __future__ import annotations

import shutil
from pathlib import Path

from .contract import SHARED_DOCS, CheckResult

DATA_DIRS = ["memories", "chapters"]
# (source in repo, destination in workspace) — copied only if absent, so a
# writer's living documents are never clobbered by a re-run.
SEEDED_FILES = [
    ("project_state.md", "project_state.md"),
    ("memories/style_guide.md", "memories/style_guide.md"),
] + [(d, d) for d in SHARED_DOCS]


def init(repo: Path, workspace: Path) -> list[str]:
    """Scaffold the workspace. Idempotent; never overwrites existing files."""
    created: list[str] = []
    workspace.mkdir(parents=True, exist_ok=True)
    for d in DATA_DIRS:
        p = workspace / d
        if not p.exists():
            p.mkdir(parents=True)
            created.append(d + "/")
    for src_rel, dest_rel in SEEDED_FILES:
        src, dest = repo / src_rel, workspace / dest_rel
        if dest.exists():
            continue
        if not src.exists():
            raise FileNotFoundError(f"template missing from repo: {src_rel}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        created.append(dest_rel)
    return created


def doctor(workspace: Path) -> list[CheckResult]:
    checks: list[CheckResult] = []
    ok = workspace.is_dir()
    checks.append(
        CheckResult(
            "workspace exists", ok, str(workspace),
            fix="run: memoir init --workspace <path>",
        )
    )
    if not ok:
        return checks
    for d in DATA_DIRS:
        checks.append(
            CheckResult(
                f"{d}/ directory", (workspace / d).is_dir(),
                fix="run: memoir init (idempotent)",
            )
        )
    for _, dest_rel in SEEDED_FILES:
        checks.append(
            CheckResult(
                dest_rel, (workspace / dest_rel).is_file(),
                fix="run: memoir init (idempotent)",
            )
        )
    return checks
