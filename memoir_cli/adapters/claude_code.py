"""Reference adapter: Claude Code (headless `claude -p` + OS scheduler).

Safety is enforced at the tool-permission layer, not just in prompt text:
autonomous runs get a generated settings file whose permission rules DENY
Write/Edit under chapters/ — the truth contract as a mechanism (ROADMAP P1/P2).
"""

from __future__ import annotations

import json
import re
import shlex
import shutil
import subprocess
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

# capability-contract.md tool-name mapping, as code.
TOOL_MAP = {
    "read_file": ["Read"],
    "write_file": ["Write", "Edit"],
    "list_directory": ["Glob"],
    "text-generation": [],  # implicit in the model
    "memory": [],           # state lives in workspace files
}

# Tools an AUTONOMOUS run may use. Write stays available for memories/ and
# project_state.md; chapters/ is denied by permission rules below.
AUTONOMOUS_TOOLS = "Read,Glob,Grep,Write,Edit"

AUTONOMOUS_SETTINGS = {
    "permissions": {
        "deny": [
            "Write(./chapters/**)",
            "Edit(./chapters/**)",
            "Bash",
            "WebFetch",
        ]
    }
}

CRON_BEGIN = "# >>> memoir-agent (managed block, do not edit) >>>"
CRON_END = "# <<< memoir-agent <<<"

# Launcher for the stateful driver (retries, quiet hours, delivery, run log).
MEMOIR_BIN = Path(__file__).resolve().parents[2] / "bin" / "memoir"

_ALLOWED_TOOLS_RE = re.compile(
    r"^allowed-tools:\n(?:^[ \t]+-[^\n]*\n)+", flags=re.M
)


def map_allowed_tools(skill_md: str) -> str:
    """Rewrite the frontmatter allowed-tools block to Claude Code tool names."""
    m = _ALLOWED_TOOLS_RE.search(skill_md)
    if not m:
        return skill_md
    declared = re.findall(r"^[ \t]+-[ \t]*(\S+)", m.group(0), flags=re.M)
    mapped: list[str] = []
    for tool in declared:
        for real in TOOL_MAP.get(tool, [tool]):
            if real not in mapped:
                mapped.append(real)
    block = "allowed-tools:\n" + "".join(f"  - {t}\n" for t in mapped)
    return skill_md[: m.start()] + block + skill_md[m.end():]


class ClaudeCodeAdapter(Adapter):
    id = "claude-code"
    label = "Claude Code (headless CLI + OS scheduler)"

    @classmethod
    def detect(cls) -> Detection:
        path = shutil.which("claude")
        return Detection(cls.id, path is not None, {"claude": path or "not found"})

    # -- C2 -------------------------------------------------------------
    def skills_root(self, workspace: Path) -> Path:
        return workspace / ".claude" / "skills"

    def install_skills(self, repo: Path, workspace: Path) -> list[str]:
        root = self.skills_root(workspace)
        root.mkdir(parents=True, exist_ok=True)
        installed: list[str] = []
        for name in SKILL_DIRS:
            src = repo / name
            if not src.is_dir():
                raise FileNotFoundError(f"skill missing from repo: {name}")
            dest = root / name
            copy_skill_dir(src, dest)
            skill_md = dest / "SKILL.md"
            skill_md.write_text(
                map_allowed_tools(skill_md.read_text(encoding="utf-8")),
                encoding="utf-8",
            )
            installed.append(name)
        return installed

    def agent_command(self, workspace: Path, prompt: str) -> str:
        settings = memoir_dir(workspace) / "autonomous-settings.json"
        return (
            f"cd {shlex.quote(str(workspace))} && "
            f"claude -p {shlex.quote(prompt)} "
            f"--settings {shlex.quote(str(settings))} "
            f"--allowedTools {shlex.quote(AUTONOMOUS_TOOLS)}"
        )

    def reply_command(self, workspace: Path, prompt: str) -> str:
        """Reply turns continue the most recent session in the workspace, so the
        agent remembers what it asked. Same guardrails as autonomous runs: a
        reply is still unattended — drafting stays in interactive sessions."""
        settings = memoir_dir(workspace) / "autonomous-settings.json"
        return (
            f"cd {shlex.quote(str(workspace))} && "
            f"claude -p --continue {shlex.quote(prompt)} "
            f"--settings {shlex.quote(str(settings))} "
            f"--allowedTools {shlex.quote(AUTONOMOUS_TOOLS)}"
        )

    # -- C3 -------------------------------------------------------------
    def schedule(
        self, workspace: Path, jobs: list[Job], notify_cmd: str
    ) -> tuple[list[Path], str]:
        d = memoir_dir(workspace)
        artifacts: list[Path] = []

        settings = d / "autonomous-settings.json"
        settings.write_text(
            json.dumps(AUTONOMOUS_SETTINGS, indent=2) + "\n", encoding="utf-8"
        )
        artifacts.append(settings)

        # ensure the driver (`memoir run`) knows which adapter owns this
        # workspace, even when schedule() is called programmatically
        cfg_path = d / "config.json"
        cfg = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
        cfg["adapter"] = self.id
        cfg_path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")

        # crontab block — every unattended turn goes through the stateful driver
        # (`memoir run`): retries, quiet-hours guard, delivery, structured logs.
        def driver_cmd(job: Job) -> str:
            return (
                f"{shlex.quote(str(MEMOIR_BIN))} run "
                f"--workspace {shlex.quote(str(workspace))} --job {job.id}"
            )

        lines = [CRON_BEGIN]
        for job in jobs:
            lines.append(f"# {job.description}")
            lines.append(
                f"{job.cron} {driver_cmd(job)} >>{shlex.quote(str(d / 'cron.log'))} 2>&1"
            )
        lines.append(CRON_END)
        cron_file = d / "cron.txt"
        cron_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        artifacts.append(cron_file)

        # systemd user units (alternative to cron)
        sysd = d / "systemd"
        sysd.mkdir(exist_ok=True)
        for job in jobs:
            unit = sysd / f"memoir-{job.id}.service"
            unit.write_text(
                "[Unit]\n"
                f"Description=memoir: {job.description}\n\n"
                "[Service]\nType=oneshot\n"
                f"ExecStart={MEMOIR_BIN} run --workspace {workspace} --job {job.id}\n",
                encoding="utf-8",
            )
            timer = sysd / f"memoir-{job.id}.timer"
            timer.write_text(
                "[Unit]\n"
                f"Description=memoir timer: {job.description}\n\n"
                "[Timer]\n"
                f"OnCalendar={job.on_calendar}\nPersistent=true\n\n"
                "[Install]\nWantedBy=timers.target\n",
                encoding="utf-8",
            )
            artifacts += [unit, timer]

        instructions = (
            "Activate ONE of:\n"
            f"  cron:    memoir schedule --apply   (merges {cron_file} into your crontab)\n"
            f"  systemd: cp {sysd}/*.service {sysd}/*.timer ~/.config/systemd/user/ && "
            "systemctl --user daemon-reload && "
            "systemctl --user enable --now memoir-daily-nudge.timer memoir-weekly-review.timer\n"
            "Safety: autonomous runs use autonomous-settings.json — Write/Edit denied "
            "under chapters/, Bash and WebFetch denied entirely."
        )
        return artifacts, instructions

    def apply_cron(self, workspace: Path) -> str:
        """Merge the managed block into the user's crontab (marker-delimited)."""
        cron_file = memoir_dir(workspace) / "cron.txt"
        if not cron_file.exists():
            raise SystemExit("no cron.txt — run `memoir schedule` first")
        if shutil.which("crontab") is None:
            raise SystemExit("crontab not found on PATH — use the systemd units instead")
        current = subprocess.run(
            ["crontab", "-l"], capture_output=True, text=True
        ).stdout
        kept: list[str] = []
        skipping = False
        for line in current.splitlines():
            if line.strip() == CRON_BEGIN:
                skipping = True
                continue
            if line.strip() == CRON_END:
                skipping = False
                continue
            if not skipping:
                kept.append(line)
        new = "\n".join(kept).rstrip("\n")
        new = (new + "\n\n" if new else "") + cron_file.read_text(encoding="utf-8")
        subprocess.run(["crontab", "-"], input=new, text=True, check=True)
        return "crontab updated (managed block replaced)"

    # -- doctor -----------------------------------------------------------
    def doctor(self, repo: Path, workspace: Path) -> list[CheckResult]:
        checks: list[CheckResult] = []
        det = self.detect()
        checks.append(
            CheckResult(
                "claude CLI on PATH", det.available, det.details["claude"],
                fix="install Claude Code: https://claude.com/claude-code",
            )
        )
        root = self.skills_root(workspace)
        for name in SKILL_DIRS:
            checks.append(
                CheckResult(
                    f"skill installed: {name}",
                    (root / name / "SKILL.md").is_file(),
                    fix="run: memoir install",
                )
            )
        d = workspace / ".memoir"
        settings = d / "autonomous-settings.json"
        deny_ok = False
        if settings.is_file():
            try:
                deny = json.loads(settings.read_text())["permissions"]["deny"]
                deny_ok = any("chapters" in rule for rule in deny)
            except (json.JSONDecodeError, KeyError):
                deny_ok = False
        checks.append(
            CheckResult(
                "autonomous runs cannot write chapters/ (deny rules)", deny_ok,
                fix="run: memoir schedule",
            )
        )
        checks.append(
            CheckResult(
                "scheduler artifacts generated", (d / "cron.txt").is_file(),
                fix="run: memoir schedule",
            )
        )
        checks.append(
            CheckResult(
                "driver config present (memoir run)", (d / "config.json").is_file(),
                fix="run: memoir schedule",
            )
        )
        notify = d / "notify.sh"
        checks.append(
            CheckResult(
                "notifier configured", notify.is_file(),
                fix="run: memoir schedule --notify <ntfy|telegram|slack|file> ...",
            )
        )
        if shutil.which("crontab"):
            current = subprocess.run(
                ["crontab", "-l"], capture_output=True, text=True
            ).stdout
            checks.append(
                CheckResult(
                    "crontab contains managed block", CRON_BEGIN in current,
                    fix="run: memoir schedule --apply (or use the systemd units)",
                )
            )
        return checks
