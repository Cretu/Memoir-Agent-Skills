#!/usr/bin/env python3
"""Repository validator for Memoir Agent Skills.

Stdlib-only. Run from the repo root (or pass the root as argv[1]):

    python3 scripts/validate.py

Checks:
  1. Every skill dir (memoir-*/ containing SKILL.md) has valid frontmatter:
     - `name` and `description` present
     - `name` matches the directory name
     - `description` is <= 160 bytes (OpenClaw hard limit; good hygiene everywhere)
  2. SKILL.yaml exists beside SKILL.md and its `name` matches.
  3. No legacy support-file layout (reference.md / EXAMPLES.md / prompts/ at the
     skill root — they belong under references/, examples/, templates/).
  4. .claude/skills.json parses, and every skill/reference path it lists exists.
  5. All relative markdown links in *.md resolve to a real file or directory
     (fenced code blocks and inline code are ignored; http/mailto/# skipped).
  6. Required top-level docs exist.

Exit code 0 = all good; 1 = at least one error. Warnings never fail the build.
"""

import json
import re
import sys
from pathlib import Path

DESC_BYTE_LIMIT = 160

REQUIRED_DOCS = [
    "README.md",
    "orchestration.md",
    "project_state.md",
    "memoir-ethics-and-care.md",
    "memoir-purpose-and-audience.md",
    "deployment/README.md",
    "deployment/capability-contract.md",
    "deployment/detect-runtime.sh",
]

LEGACY_LAYOUT = ["reference.md", "EXAMPLES.md", "prompts"]

errors: list[str] = []
warnings: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


def parse_simple_yaml(text: str) -> dict:
    """Parse top-level `key: value` pairs, supporting folded scalars (> / >-).

    Good enough for SKILL frontmatter; not a general YAML parser.
    """
    data: dict[str, str] = {}
    key = None
    folded: list[str] = []
    for line in text.splitlines():
        m = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if m:
            if key is not None:
                data[key] = " ".join(folded).strip()
            k, v = m.group(1), m.group(2).strip()
            if v in (">", ">-", "|", "|-"):
                key, folded = k, []
            else:
                data[k] = v
                key, folded = None, []
        elif key is not None and (line.startswith(" ") or line.startswith("\t")):
            folded.append(line.strip())
        elif key is not None and not line.strip():
            folded.append("")
        else:
            key, folded = None, []
    if key is not None:
        data[key] = " ".join(folded).strip()
    return data


def frontmatter(path: Path) -> dict | None:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, flags=re.S)
    return parse_simple_yaml(m.group(1)) if m else None


def check_skills(root: Path) -> list[Path]:
    skill_dirs = sorted(
        d for d in root.glob("memoir-*") if d.is_dir() and (d / "SKILL.md").exists()
    )
    if not skill_dirs:
        err("no skill directories found (memoir-*/SKILL.md)")
        return []

    for d in skill_dirs:
        rel = d.name
        fm = frontmatter(d / "SKILL.md")
        if fm is None:
            err(f"{rel}/SKILL.md: missing YAML frontmatter (--- block)")
            continue
        name = fm.get("name", "")
        desc = fm.get("description", "")
        if not name:
            err(f"{rel}/SKILL.md: frontmatter missing `name`")
        elif name != rel:
            err(f"{rel}/SKILL.md: frontmatter name {name!r} != directory name {rel!r}")
        if not desc:
            err(f"{rel}/SKILL.md: frontmatter missing `description`")
        else:
            nbytes = len(desc.encode("utf-8"))
            if nbytes > DESC_BYTE_LIMIT:
                err(
                    f"{rel}/SKILL.md: description is {nbytes} bytes "
                    f"(limit {DESC_BYTE_LIMIT})"
                )

        yaml_path = d / "SKILL.yaml"
        if not yaml_path.exists():
            err(f"{rel}/: missing SKILL.yaml")
        else:
            meta = parse_simple_yaml(yaml_path.read_text(encoding="utf-8"))
            if meta.get("name", "") != rel:
                err(f"{rel}/SKILL.yaml: name {meta.get('name')!r} != {rel!r}")

        for legacy in LEGACY_LAYOUT:
            if (d / legacy).exists():
                err(
                    f"{rel}/{legacy}: legacy layout — move to "
                    "references/, examples/, or templates/"
                )
    return skill_dirs


def check_manifest(root: Path, skill_dirs: list[Path]) -> None:
    manifest = root / ".claude" / "skills.json"
    if not manifest.exists():
        warn(".claude/skills.json not found (optional manifest)")
        return
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        err(f".claude/skills.json: invalid JSON — {e}")
        return

    listed = set()
    for entry in data.get("skills", []) + data.get("shared_references", []):
        p = entry.get("path", "")
        listed.add(Path(p).name)
        if not (root / p).exists():
            err(f".claude/skills.json: path {p!r} does not exist")

    for d in skill_dirs:
        if d.name not in listed:
            warn(f".claude/skills.json: skill {d.name!r} is not listed in the manifest")


LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
FENCE_RE = re.compile(r"```.*?```", flags=re.S)
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")


def check_links(root: Path) -> None:
    for md in sorted(root.rglob("*.md")):
        if ".git" in md.parts:
            continue
        text = md.read_text(encoding="utf-8")
        text = FENCE_RE.sub("", text)
        text = INLINE_CODE_RE.sub("", text)
        for target in LINK_RE.findall(text):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            path_part = target.split("#", 1)[0]
            if not path_part:
                continue
            resolved = (md.parent / path_part).resolve()
            if not resolved.exists():
                err(f"{md.relative_to(root)}: broken link -> {target}")


def check_required_docs(root: Path) -> None:
    for doc in REQUIRED_DOCS:
        if not (root / doc).exists():
            err(f"required file missing: {doc}")


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    if not (root / "orchestration.md").exists():
        print(f"error: {root} does not look like the repo root", file=sys.stderr)
        return 2

    skill_dirs = check_skills(root)
    check_manifest(root, skill_dirs)
    check_required_docs(root)
    check_links(root)

    for w in warnings:
        print(f"  warn: {w}")
    if errors:
        for e in errors:
            print(f"  FAIL: {e}")
        print(f"\nvalidate: {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    print(
        f"validate: OK — {len(skill_dirs)} skills checked, "
        f"{len(warnings)} warning(s)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
