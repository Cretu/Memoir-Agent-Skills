"""Where the skill bundle lives, in each of the ways this can be installed.

`memoir install` copies real files (SKILL.md and friends) into the runtime, so
the CLI must find them whether it is running from a git checkout, from a wheel
installed into site-packages, or from a bundle the writer unpacked somewhere.
Resolution order, first hit wins:

1. ``$MEMOIR_SKILLS_DIR`` — an explicit override, always respected.
2. Staged package data (``memoir_cli/_skills/``) — how a wheel ships the
   bundle; created by ``scripts/stage_bundle.py`` at build time.
3. The repository checkout above the package — how it runs from a clone.

If none holds a real bundle, say so with the fix, rather than failing later
with a confusing "skill missing from repo" halfway through an install.
"""

from __future__ import annotations

import os
from pathlib import Path

# A directory is a bundle root if it has the shared docs and at least the
# orchestrator skill; checking two independent markers avoids matching an empty
# staging directory left behind by a failed build.
MARKERS = ("orchestration.md", "memoir-orchestrator/SKILL.md")

STAGED_DIRNAME = "_skills"


def _is_bundle_root(path: Path) -> bool:
    return all((path / marker).exists() for marker in MARKERS)


def candidates() -> list[tuple[str, Path]]:
    here = Path(__file__).resolve()
    out = []
    env = os.environ.get("MEMOIR_SKILLS_DIR", "").strip()
    if env:
        out.append(("MEMOIR_SKILLS_DIR", Path(env).expanduser()))
    out.append(("packaged bundle", here.parent / STAGED_DIRNAME))
    out.append(("repository checkout", here.parents[1]))
    return out


def repo_root() -> Path:
    """The directory holding the skill bundle and shared documents."""
    tried = []
    for label, path in candidates():
        if _is_bundle_root(path):
            return path
        tried.append(f"  {label}: {path}")
    raise SystemExit(
        "cannot find the memoir skill bundle. Looked in:\n"
        + "\n".join(tried)
        + "\n\nFix: run from a repository checkout, reinstall the package, or set\n"
        "  MEMOIR_SKILLS_DIR=/path/to/bundle"
    )


def describe() -> str:
    for label, path in candidates():
        if _is_bundle_root(path):
            return f"{path} ({label})"
    return "(not found)"
