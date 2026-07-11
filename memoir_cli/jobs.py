"""C3 — the standard proactive jobs (daily nudge + weekly review)."""

from __future__ import annotations

from .contract import AUTONOMOUS_PREAMBLE, NO_PROSE_CLAUSE, Job

_DOW_CRON = {"mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6, "sun": 0}
_DOW_SYSTEMD = {
    "mon": "Mon", "tue": "Tue", "wed": "Wed", "thu": "Thu",
    "fri": "Fri", "sat": "Sat", "sun": "Sun",
}

DAILY_PROMPT = (
    AUTONOMOUS_PREAMBLE
    + "output ONE concrete 15-minute memoir task plus an easy reply hook "
      "(one short, phone-friendly message)." + NO_PROSE_CLAUSE
)
WEEKLY_PROMPT = (
    AUTONOMOUS_PREAMBLE
    + "output a short weekly review: progress this week, the chapter board, and a "
      "proposed (not imposed) cadence for next week in the memoir-coach's voice."
    + NO_PROSE_CLAUSE
)

# Used by `memoir run --reply` (driver.py): the writer answered a nudge.
REPLY_PREAMBLE = (
    "The writer replied to a memoir nudge. As memoir-orchestrator: acknowledge "
    "briefly and warmly, capture any memory material they shared into memories/ "
    "as a draft Memory Capture (record only what they actually said — never "
    "fabricate detail), update project_state.md (snapshot + momentum), and end "
    "with ONE gentle next step or question." + NO_PROSE_CLAUSE
    + "\n\nWriter's reply:\n"
)


def _parse_hhmm(value: str) -> tuple[int, int]:
    hh, mm = value.split(":", 1)
    h, m = int(hh), int(mm)
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ValueError(f"invalid time: {value!r}")
    return h, m


def standard_jobs(
    daily_time: str = "20:00",
    weekly_day: str = "sun",
    weekly_time: str = "19:00",
) -> list[Job]:
    """The default proactive schedule, with writer-chosen times."""
    dh, dm = _parse_hhmm(daily_time)
    wh, wm = _parse_hhmm(weekly_time)
    day = weekly_day.lower()[:3]
    if day not in _DOW_CRON:
        raise ValueError(f"invalid weekday: {weekly_day!r}")
    return [
        Job(
            id="daily-nudge",
            description="Daily 15-minute memoir task",
            cron=f"{dm} {dh} * * *",
            on_calendar=f"*-*-* {dh:02d}:{dm:02d}:00",
            prompt=DAILY_PROMPT,
        ),
        Job(
            id="weekly-review",
            description="Weekly progress review",
            cron=f"{wm} {wh} * * {_DOW_CRON[day]}",
            on_calendar=f"{_DOW_SYSTEMD[day]} *-*-* {wh:02d}:{wm:02d}:00",
            prompt=WEEKLY_PROMPT,
        ),
    ]
