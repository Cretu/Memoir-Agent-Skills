"""Adapter: OpenClaw. Provides C1-C4 natively; this adapter installs skills to
the workspace skills root and emits ready-to-run `openclaw cron create` commands
(deployment/adapters/openclaw.md documents the manual path in full)."""

from __future__ import annotations

import shlex
import shutil
from pathlib import Path

from ..contract import (
    SKILL_DIRS,
    Adapter,
    CheckResult,
    Detection,
    Job,
    copy_skill_dir,
    memoir_dir,
)


class OpenClawAdapter(Adapter):
    id = "openclaw"
    label = "OpenClaw (native cron + heartbeat + channels)"

    def __init__(self, channel: str = "telegram", to: str = "<your-chat-id>"):
        self.channel = channel
        self.to = to

    @classmethod
    def detect(cls) -> Detection:
        path = shutil.which("openclaw")
        return Detection(cls.id, path is not None, {"openclaw": path or "not found"})

    def skills_root(self, workspace: Path) -> Path:
        return workspace / "skills"

    def install_skills(self, repo: Path, workspace: Path) -> list[str]:
        root = self.skills_root(workspace)
        root.mkdir(parents=True, exist_ok=True)
        installed = []
        for name in SKILL_DIRS:
            src = repo / name
            if not src.is_dir():
                raise FileNotFoundError(f"skill missing from repo: {name}")
            copy_skill_dir(src, root / name)
            installed.append(name)
        return installed

    def agent_command(self, workspace: Path, prompt: str) -> str:
        # OpenClaw invokes the agent itself; this is only used in emitted
        # cron-create commands where the prompt is the payload.
        return prompt

    def schedule(
        self, workspace: Path, jobs: list[Job], notify_cmd: str
    ) -> tuple[list[Path], str]:
        # C4 is native (channels); notify_cmd is unused here.
        d = memoir_dir(workspace)
        script = d / "openclaw-cron.sh"
        lines = ["#!/bin/sh", "# Run once to register the memoir jobs with OpenClaw."]
        for job in jobs:
            lines.append(
                "openclaw cron create "
                + shlex.quote(job.cron.replace("  ", " "))
                + f" {shlex.quote(job.prompt)}"
                + f" --name {shlex.quote('memoir ' + job.id)}"
                + " --session isolated --announce"
                + f" --channel {shlex.quote(self.channel)} --to {shlex.quote(self.to)}"
            )
        script.write_text("\n".join(lines) + "\n", encoding="utf-8")
        script.chmod(0o700)
        instructions = (
            f"Register the jobs: sh {script}\n"
            "Delivery uses OpenClaw's native channels (C4); adjust --channel/--to first.\n"
            "Safety: the no-finalize rule is in each job prompt and in the "
            "Orchestrator skill; OpenClaw's tool policy can additionally restrict "
            "writes under chapters/."
        )
        return [script], instructions

    def doctor(self, repo: Path, workspace: Path) -> list[CheckResult]:
        det = self.detect()
        checks = [
            CheckResult(
                "openclaw CLI on PATH", det.available, det.details["openclaw"],
                fix="https://openclaw.ai",
            )
        ]
        root = self.skills_root(workspace)
        for name in SKILL_DIRS:
            checks.append(
                CheckResult(
                    f"skill installed: {name}",
                    (root / name / "SKILL.md").is_file(),
                    fix="run: memoir install --adapter openclaw",
                )
            )
        checks.append(
            CheckResult(
                "cron registration script generated",
                (workspace / ".memoir" / "openclaw-cron.sh").is_file(),
                fix="run: memoir schedule --adapter openclaw",
            )
        )
        return checks
