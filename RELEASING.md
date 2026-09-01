# Releasing

One version number covers the Python package, the skill bundles and the
changelog. `scripts/validate.py` fails the build if a released version has no
`CHANGELOG.md` section, so the notes cannot silently fall behind the code.

## Cut a release

1. **Decide the version** (semver). Breaking the workspace data model or a skill
   contract is a major; new capability is a minor; fixes are a patch.
2. **Update `memoir_cli/__init__.py`** — `__version__ = "X.Y.Z"`.
3. **Move `CHANGELOG.md`'s `[Unreleased]` items** under a new
   `## [X.Y.Z] — YYYY-MM-DD` heading, leaving an empty `[Unreleased]` above it.
4. **`make all`** — validator (including the version/changelog check), tests,
   shell lint, and the truth-contract eval must be green.
5. **Build the artifacts**:
   ```sh
   make dist      # stages the bundle into the package, builds the wheel
   make bundle    # tar + claude-plugin + openclaw trees under dist/
   ```
6. **Verify the wheel outside a checkout** (CI does this too, but do it once by
   hand before a real publish):
   ```sh
   python3 -m venv /tmp/v && /tmp/v/bin/pip install dist/*.whl
   cd /tmp && /tmp/v/bin/memoir setup --workspace /tmp/ws --adapter claude-code --notify file
   /tmp/v/bin/memoir doctor --workspace /tmp/ws --adapter claude-code
   ```
7. **Tag and push**: `git tag vX.Y.Z && git push origin vX.Y.Z`.

## Publishing per channel

| Channel | Artifact | Notes |
|---|---|---|
| PyPI | `dist/*.whl`, `dist/*.tar.gz` | `python3 -m twine upload dist/*` |
| Claude Code plugin | `dist/memoir-agent/` | **Validate with the local Claude Code plugin tooling before publishing** — `memoir bundle` writes the layout, it cannot check it against the live plugin schema. |
| OpenClaw / ClawHub | `dist/memoir-openclaw-X.Y.Z/` | drop `skills/` into the workspace; register jobs with `memoir schedule --adapter openclaw` |
| Plain tarball | `dist/memoir-skills-X.Y.Z.tar.gz` | carries `MANIFEST.json`; recipients can re-check it |

## Verifying a bundle after it travels

Every generated bundle carries a `MANIFEST.json` with a sha256 per file:

```python
from pathlib import Path
from memoir_cli import bundle
ok, problems = bundle.verify(Path("memoir-skills-X.Y.Z"))
```

## What is *not* automated

Publishing itself. No workflow holds registry credentials, and nothing uploads
on a tag — a human runs the upload deliberately. That is the intended trade-off
for a project whose artifact is someone's life story.
