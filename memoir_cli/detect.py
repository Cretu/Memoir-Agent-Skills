"""`memoir detect` — structured, read-only host probe (python port of
deployment/detect-runtime.sh with JSON output)."""

from __future__ import annotations

import shutil
from pathlib import Path

from .adapters import ADAPTERS
from .adapters.generic import GenericCronAdapter


def probe(workspace: Path | None = None) -> dict:
    runtimes = {
        aid: cls.detect().available
        for aid, cls in ADAPTERS.items()
        if cls is not GenericCronAdapter
    }
    schedulers = {
        "cron": shutil.which("crontab") is not None,
        "launchd": shutil.which("launchctl") is not None,
        "systemd": shutil.which("systemctl") is not None,
    }
    notifiers = {
        "curl": shutil.which("curl") is not None,
        "mail": shutil.which("mail") is not None or shutil.which("sendmail") is not None,
    }
    recommended = next((aid for aid, ok in runtimes.items() if ok), "generic")
    report: dict = {
        "runtimes": runtimes,
        "schedulers": schedulers,
        "notifiers": notifiers,
        "recommended_adapter": recommended,
        "semi_auto_only": not any(schedulers.values()) and recommended != "openclaw",
    }
    if workspace is not None:
        report["workspace_initialized"] = (workspace / "project_state.md").is_file()
    return report


def render(report: dict) -> str:
    def mark(ok: bool) -> str:
        return "[x]" if ok else "[ ]"

    lines = ["Runtimes:"]
    lines += [f"  {mark(ok)} {rid}" for rid, ok in report["runtimes"].items()]
    lines.append("Schedulers (C3):")
    lines += [f"  {mark(ok)} {s}" for s, ok in report["schedulers"].items()]
    lines.append("Notifiers (C4):")
    lines += [f"  {mark(ok)} {n}" for n, ok in report["notifiers"].items()]
    lines.append(f"Recommended adapter: {report['recommended_adapter']}")
    if report.get("semi_auto_only"):
        lines.append(
            "No scheduler found -> semi-auto mode (you open each session); "
            "see deployment/README.md"
        )
    return "\n".join(lines)
