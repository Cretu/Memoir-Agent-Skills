"""The caring adaptive engine (ROADMAP Phase 3).

Decides, before each scheduled nudge, whether to send at all and in what tone —
from the writer's actual response signals, not a fixed cron beat:

  * pause / quiet dates (care.json)  -> never nudge, full stop
  * silence                          -> back OFF, don't badger: the longer the
    writer hasn't replied, the LOWER the frequency and the softer the ask
  * a reply                          -> resets the ladder instantly

Hard rules: escalation only ever goes down (gentler, rarer), never up; replies
are handled whenever they arrive; the writer's own cadence choice is the
ceiling, silence only widens the gap below it.
"""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass
from pathlib import Path

from . import care as care_mod
from . import driver as driver_mod
from .contract import memoir_dir

# The backoff ladder: streak of unanswered nudges -> (min days between nudges,
# soften the ask?). Base gap comes from the writer's cadence; the ladder can
# only widen it.
LADDER = [
    (0, 1.0, False),   # replying recently: writer's own cadence, normal tone
    (3, 2.0, True),    # 3+ unanswered: at most every 2 days, soften
    (6, 7.0, True),    # 6+ unanswered: weekly floor, soften
]


@dataclass
class Decision:
    send: bool
    soften: bool
    reason: str
    silent_streak: int


def _delivered_nudges(workspace: Path) -> list[dt.datetime]:
    """Timestamps of successfully delivered daily nudges, oldest first."""
    runs_file = memoir_dir(workspace) / "runs.jsonl"
    if not runs_file.exists():
        return []
    out = []
    for raw in runs_file.read_text(encoding="utf-8").splitlines():
        try:
            e = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if e.get("kind") == "job" and e.get("id") == "daily-nudge" and e.get("delivered"):
            try:
                out.append(dt.datetime.fromisoformat(e["ts"]))
            except (KeyError, ValueError):
                continue
    return out


def silent_streak(workspace: Path) -> tuple[int, dt.datetime | None]:
    """(number of delivered nudges since the writer's last reply, ts of the
    most recent delivered nudge)."""
    nudges = _delivered_nudges(workspace)
    if not nudges:
        return 0, None
    last_reply = driver_mod.load_state(workspace).get("last_reply_at")
    if last_reply:
        cutoff = dt.datetime.fromisoformat(last_reply)
        unanswered = [ts for ts in nudges if ts > cutoff]
    else:
        unanswered = nudges
    return len(unanswered), nudges[-1]


def decide(workspace: Path, now: dt.datetime | None = None) -> Decision:
    now = now or dt.datetime.now(dt.timezone.utc)
    today = now.astimezone().date()
    care = care_mod.load(workspace)

    if care_mod.is_paused(care, today):
        return Decision(False, False, f"paused until {care['pause_until']}", 0)
    reason = care_mod.quiet_date_reason(care, today)
    if reason:
        return Decision(False, False, f"quiet dates: {reason}", 0)

    streak, last_nudge = silent_streak(workspace)

    base_gap = 7.0 / care.get("cadence", {}).get("nudges_per_week", 7)
    gap_days, soften = base_gap, False
    for threshold, ladder_gap, ladder_soften in LADDER:
        if streak >= threshold:
            gap_days, soften = max(base_gap, ladder_gap), ladder_soften

    if last_nudge is not None:
        elapsed = (now - last_nudge).total_seconds() / 86400
        if elapsed < gap_days:
            return Decision(
                False, soften,
                f"backing off: {streak} unanswered nudge(s), "
                f"next one {gap_days:.0f}d apart ({elapsed:.1f}d elapsed)",
                streak,
            )

    reason = "normal cadence" if not soften else (
        f"sending softly: {streak} unanswered nudge(s) — smaller ask, no pressure"
    )
    return Decision(True, soften, reason, streak)
