"""Fallback adapter: any headless agent CLI + OS cron. The agent command is
supplied by the user (--agent-cmd) and persisted in .memoir/config.json."""

from __future__ import annotations

import json
import shlex
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


class GenericCronAdapter(Adapter):
    id = "generic"
    label = "Generic (any agent CLI + cron)"

    def __init__(self, agent_cmd: str = ""):
        self.agent_cmd = agent_cmd

    @classmethod
    def detect(cls) -> Detection:
        # Always available as the fallback; usefulness depends on --agent-cmd.
        return Detection(cls.id, True, {"note": "fallback; requires --agent-cmd"})

    def _config(self, workspace: Path) -> Path:
        return memoir_dir(workspace) / "config.json"

    def _load_agent_cmd(self, workspace: Path) -> str:
        if self.agent_cmd:
            return self.agent_cmd
        cfg = self._config(workspace)
        if cfg.exists():
            return json.loads(cfg.read_text()).get("agent_cmd", "")
        return ""

    def install_skills(self, repo: Path, workspace: Path) -> list[str]:
        # No known discovery mechanism: stage the bundle under skills/ and let
        # the user's CLI ingest it (system prompt or --include equivalent).
        root = workspace / "skills"
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
        cmd = self._load_agent_cmd(workspace)
        if not cmd:
            raise SystemExit(
                "generic adapter needs --agent-cmd (a shell template containing "
                "{prompt}), e.g. --agent-cmd 'my-agent --once {prompt}'"
            )
        if "{prompt}" not in cmd:
            raise SystemExit("--agent-cmd must contain the {prompt} placeholder")
        return f"cd {shlex.quote(str(workspace))} && " + cmd.replace(
            "{prompt}", shlex.quote(prompt)
        )

    def schedule(
        self, workspace: Path, jobs: list[Job], notify_cmd: str
    ) -> tuple[list[Path], str]:
        cmd = self._load_agent_cmd(workspace)
        if cmd:
            self._config(workspace).write_text(
                json.dumps({"adapter": self.id, "agent_cmd": cmd}, indent=2) + "\n",
                encoding="utf-8",
            )
        d = memoir_dir(workspace)
        cron_file = d / "cron.txt"
        lines = []
        for job in jobs:
            lines.append(f"# {job.description}")
            lines.append(
                f"{job.cron} {self.agent_command(workspace, job.prompt)} | {notify_cmd}"
            )
        cron_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        instructions = (
            f"Add the lines in {cron_file} to your scheduler "
            "(crontab -e, or translate to launchd/systemd — see "
            "deployment/adapters/generic-cron.md)."
        )
        return [cron_file], instructions

    def doctor(self, repo: Path, workspace: Path) -> list[CheckResult]:
        cmd = self._load_agent_cmd(workspace)
        checks = [
            CheckResult(
                "agent command configured", bool(cmd),
                cmd or "", fix="run: memoir schedule --agent-cmd '... {prompt} ...'",
            ),
            CheckResult(
                "skills staged", (workspace / "skills").is_dir(),
                fix="run: memoir install --adapter generic",
            ),
            CheckResult(
                "cron lines generated",
                (workspace / ".memoir" / "cron.txt").is_file(),
                fix="run: memoir schedule --adapter generic",
            ),
        ]
        return checks
