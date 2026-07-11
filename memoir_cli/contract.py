"""The capability contract (C1-C4) as code.

Mirrors deployment/capability-contract.md:
  C1 files - the workspace data model (handled by workspace.py, shared)
  C2 skills - install_skills() + agent_command() (how the runtime loads/runs them)
  C3 schedule - schedule() (unattended invocation artifacts)
  C4 notify - handled by notify.py (shared), consumed by schedule()

Each runtime implements Adapter. The safety floor is part of the contract:
autonomous (scheduled) runs must not be able to finalize prose - adapters
enforce it as mechanically as their runtime allows (see claude_code.py for
tool-permission-level enforcement).
"""

from __future__ import annotations

import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

# The six skills plus shared docs that ship with every install.
SKILL_DIRS = [
    "memoir-orchestrator",
    "memoir-coach",
    "memoir-memory-recall",
    "memoir-architect-biographer",
    "memoir-writing",
    "memoir-revision",
]
SHARED_DOCS = [
    "orchestration.md",
    "memoir-ethics-and-care.md",
    "memoir-purpose-and-audience.md",
]

# The prompt used for every unattended run. The "no prose" clause is the
# truth contract (memoir-ethics-and-care.md Part 3) in imperative form.
AUTONOMOUS_PREAMBLE = (
    "Run the memoir-orchestrator skill in AUTONOMOUS mode: read project_state.md, "
    "honour the Care notes (quiet windows, off-limits topics), and "
)
NO_PROSE_CLAUSE = (
    " Do NOT draft, rewrite, or finalize memoir prose, and do NOT modify anything "
    "under chapters/."
)


@dataclass
class Detection:
    adapter_id: str
    available: bool
    details: dict = field(default_factory=dict)


@dataclass
class Job:
    """One scheduled invocation (C3)."""

    id: str
    description: str
    cron: str          # crontab five-field expression
    on_calendar: str   # systemd OnCalendar equivalent
    prompt: str


@dataclass
class CheckResult:
    """One doctor finding."""

    name: str
    ok: bool
    detail: str = ""
    fix: str = ""


class Adapter(ABC):
    """A runtime that can host the memoir agent. One instance per runtime."""

    id: str = ""
    label: str = ""

    # -- discovery ---------------------------------------------------------
    @classmethod
    @abstractmethod
    def detect(cls) -> Detection:
        """Probe (read-only) whether this runtime is present."""

    # -- C2: skills into the runtime ----------------------------------------
    @abstractmethod
    def install_skills(self, repo: Path, workspace: Path) -> list[str]:
        """Install the skill bundle where this runtime discovers it.

        Returns the list of installed skill names. Must be idempotent.
        """

    @abstractmethod
    def agent_command(self, workspace: Path, prompt: str) -> str:
        """The headless shell invocation that runs one agent turn (C2 + run)."""

    # -- C3: unattended invocation ------------------------------------------
    @abstractmethod
    def schedule(
        self, workspace: Path, jobs: list[Job], notify_cmd: str
    ) -> tuple[list[Path], str]:
        """Write scheduler artifacts for `jobs`, delivery piped to notify_cmd.

        Returns (artifact paths, human instructions for activating them).
        Never activates anything itself - `--apply` handles that separately
        where supported.
        """

    # -- verification --------------------------------------------------------
    @abstractmethod
    def doctor(self, repo: Path, workspace: Path) -> list[CheckResult]:
        """Verify the installation end to end."""


# ---------------------------------------------------------------------------
# Shared helpers used by adapters
# ---------------------------------------------------------------------------

def copy_skill_dir(src: Path, dest: Path) -> None:
    """Copy one skill directory (idempotent full refresh of managed content)."""
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)


def memoir_dir(workspace: Path) -> Path:
    """Per-workspace directory for generated artifacts (never memoir content)."""
    d = workspace / ".memoir"
    d.mkdir(parents=True, exist_ok=True)
    return d
