#!/usr/bin/env python3
"""Stage the skill bundle into the package so a wheel can carry it.

`memoir install` copies real skill files into the host runtime, so those files
have to travel with the distribution. Run this before `python -m build`:

    python3 scripts/stage_bundle.py

It copies the six skills plus the shared documents and workspace templates into
`memoir_cli/_skills/`, which is declared as package data in pyproject.toml and
git-ignored (it is generated, never edited).
"""

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from memoir_cli.contract import SHARED_DOCS, SKILL_DIRS  # noqa: E402
from memoir_cli.resources import STAGED_DIRNAME  # noqa: E402

EXTRA_FILES = ["project_state.md", "memories/style_guide.md"]


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    dest = repo / "memoir_cli" / STAGED_DIRNAME
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)

    for name in SKILL_DIRS:
        src = repo / name
        if not src.is_dir():
            print(f"error: missing skill {name}", file=sys.stderr)
            return 1
        shutil.copytree(src, dest / name)

    for rel in SHARED_DOCS + EXTRA_FILES:
        src = repo / rel
        if not src.is_file():
            print(f"error: missing file {rel}", file=sys.stderr)
            return 1
        (dest / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest / rel)

    count = sum(1 for _ in dest.rglob("*") if _.is_file())
    print(f"staged {len(SKILL_DIRS)} skills + {len(SHARED_DOCS + EXTRA_FILES)} "
          f"documents ({count} files) into {dest.relative_to(repo)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
