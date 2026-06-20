# Project State — Memoir Progress Ledger

This is the single source of truth for **where the memoir is and what comes next**.
The **Orchestrator** skill reads this file at the start of every session (including
autonomous/scheduled runs) and updates it at the end. Treat it as a living dashboard,
not an archive.

> If this file and the actual files in `memories/` / `chapters/` ever disagree, the
> files on disk win. The Orchestrator should re-scan and correct this ledger.

---

## 1. Snapshot

*   **Current phase**: `[Phase 0 Compass | Recall | Architect | Writing | Revision | Done]`
*   **Last session**: `[YYYY-MM-DD]` — `[one line: what actually happened]`
*   **Next action (the ONE thing)**: `[the single, concrete, ~15-minute next step]`
*   **Momentum**: `[active streak / last active date / energy read]`

## 2. Compass status
(see `memories/style_guide.md` → Project Compass; set in Phase 0)

*   [ ] Reader set (family / public / self)
*   [ ] Scope set (whole-life / single thread / vignettes)
*   [ ] Working theme set (the "so what")
*   [ ] Privacy stance set (real names / some changed / TBD)

## 3. Memory inventory
*   **Total memories captured**: `0`
*   **By era / thread**: `[e.g. childhood ×4, early career ×1]`
*   **Gaps flagged by the Architect**: `[periods or threads that are thin]`

## 4. Chapter board
(mirrors `chapter_outline.md`; one row per planned chapter)

| Ch | Title | Outlined | Recalled | Drafted | Revised | Notes |
|----|-------|----------|----------|---------|---------|-------|
| —  | —     | ⬜        | ⬜        | ⬜       | ⬜       | no outline yet |

Legend: ✅ done · 🟡 in progress · ⬜ not started

## 5. Open loops / blockers
*   `[anything waiting on a decision, a recall session, or the writer's confirmation]`

## 6. Milestones hit
*   `[date]` — `[e.g. Compass set / first memory captured / first chapter drafted]`

## 7. Care notes — **read before any nudge**
The Orchestrator and Coach MUST read this section before pushing the writer forward.
Driving the project never overrides emotional safety (see `memoir-ethics-and-care.md`).

*   **Hard / sensitive topics**: `[topics to approach gently or only on request]`
*   **Off-limits / "not yet"**: `[topics the writer asked to defer — do NOT auto-raise]`
*   **Stopping signals seen last time**: `[if any — slow down next session]`
*   **Quiet windows (do not nudge)**: `[dates/periods, e.g. an anniversary]`
