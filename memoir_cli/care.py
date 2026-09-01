"""Machine-readable care settings (ROADMAP Phase 3).

`project_state.md`'s Care notes stay the narrative source of truth for the
*agent* (topics, stopping signals). This file is the subset the *scheduler*
must obey mechanically — pause, quiet dates, cadence — kept as JSON so the
adaptive engine never has to parse prose to decide whether nudging is okay.

Changing it is a deliberate act: the writer (or the Coach walking them through
it) uses `memoir care ...`; autonomous agent runs cannot touch it (no Bash).
"""

from __future__ import annotations

import copy
import datetime as dt
import json
import os
from pathlib import Path

from .contract import memoir_dir

DEFAULT_PAUSE_DAYS = 14

DEFAULTS: dict = {
    "version": 1,
    "pause_until": None,          # ISO date; writer asked to stop for a while
    "quiet_dates": [],            # [{"from": iso, "to": iso, "reason": str}]
    "cadence": {"nudges_per_week": 7},  # writer-chosen base rhythm
}


def care_path(workspace: Path) -> Path:
    return memoir_dir(workspace) / "care.json"


def load(workspace: Path) -> dict:
    p = care_path(workspace)
    # deep copy: mutations (e.g. appending quiet dates) must never alias the
    # module-level defaults and leak between workspaces
    data = copy.deepcopy(DEFAULTS)
    if p.exists():
        try:
            data.update(json.loads(p.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            pass  # unreadable care file must fail SAFE: defaults, never crash
    return data


def save(workspace: Path, care: dict) -> None:
    p = care_path(workspace)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(care, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, p)


# -- queries the adaptive engine uses ----------------------------------------

def is_paused(care: dict, today: dt.date) -> bool:
    until = care.get("pause_until")
    return bool(until) and today <= dt.date.fromisoformat(until)


def quiet_date_reason(care: dict, today: dt.date) -> str:
    """Non-empty reason string if today falls in a quiet date range."""
    for window in care.get("quiet_dates", []):
        start = dt.date.fromisoformat(window["from"])
        end = dt.date.fromisoformat(window.get("to", window["from"]))
        if start <= today <= end:
            return window.get("reason") or "quiet dates"
    return ""


# -- mutations (CLI / Coach-guided) -------------------------------------------

def set_pause(workspace: Path, until: dt.date) -> None:
    care = load(workspace)
    care["pause_until"] = until.isoformat()
    save(workspace, care)


def clear_pause(workspace: Path) -> None:
    care = load(workspace)
    care["pause_until"] = None
    save(workspace, care)


def add_quiet_dates(workspace: Path, date_from: str, date_to: str, reason: str = "") -> None:
    dt.date.fromisoformat(date_from)  # validate early
    dt.date.fromisoformat(date_to)
    care = load(workspace)
    care.setdefault("quiet_dates", []).append(
        {"from": date_from, "to": date_to, **({"reason": reason} if reason else {})}
    )
    save(workspace, care)


def set_cadence(workspace: Path, nudges_per_week: int) -> None:
    if not 1 <= nudges_per_week <= 7:
        raise SystemExit("cadence must be between 1 and 7 nudges per week")
    care = load(workspace)
    care.setdefault("cadence", {})["nudges_per_week"] = nudges_per_week
    save(workspace, care)


def render(care: dict, today: dt.date) -> str:
    lines = [
        f"paused:      {'until ' + care['pause_until'] if is_paused(care, today) else 'no'}",
        f"cadence:     {care.get('cadence', {}).get('nudges_per_week', 7)} nudge(s)/week (base)",
    ]
    windows = care.get("quiet_dates", [])
    if windows:
        lines.append("quiet dates:")
        for w in windows:
            reason = f" — {w['reason']}" if w.get("reason") else ""
            lines.append(f"  {w['from']} → {w.get('to', w['from'])}{reason}")
    else:
        lines.append("quiet dates: none")
    return "\n".join(lines)
