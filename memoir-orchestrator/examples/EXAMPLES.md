# Orchestrator Examples

## Example 1: Resuming after two weeks away

**User Input**: "Where are we with my memoir?"

**Skill Response** (after reading `project_state.md`, `style_guide.md`, `chapter_outline.md`,
and listing `memories/` + `chapters/`):

> Welcome back. Here's where the book stands:
>
> - **Phase**: Writing (Chapter 2 of 6)
> - **Captured**: 11 memories — strong on childhood, thin on your twenties
> - **Drafted**: Chapter 1 ✅ · Chapter 2 🟡 (outline ready, not drafted)
> - **Last session** (May 30): we outlined Chapter 2, "Leaving Home"
>
> **The one next thing**: draft Chapter 2 from the four memories you already captured for it.
> Want to do that now with the Writer, or should I remind you tomorrow evening?

*(Then updates `project_state.md`: momentum note "resumed after 14 days".)*

---

## Example 2: Scheduled daily nudge (autonomous mode, via cron)

**Trigger**: `[cron] daily memoir push, 8pm`

**Skill Response** (short, phone-friendly, one task — sent to the writer's chat channel):

> Evening — quick memoir check-in. We're at 11 memories, about to draft Chapter 2.
>
> Tonight's 15 minutes: **the train ride when you first left home.** What could you see out
> the window? Just reply with whatever comes back — I'll shape it into a memory file.

*(Reads Care notes first; "leaving home" is not flagged. Logs the nudge in the ledger. Does
NOT draft prose — only invites recall.)*

---

## Example 3: Respecting the care gate

**Trigger**: `[cron] daily memoir push`

**Care notes in `project_state.md`**:
> Off-limits / "not yet": father's illness. Quiet window: June 12–14 (anniversary).

**Date**: June 13.

**Skill Response**:

> *(Today is inside a quiet window. The Orchestrator sends nothing — or, at most, a single
> no-pressure line:)*
>
> No memoir task today. Thinking of you. We'll pick it back up whenever you're ready.

*(Updates the ledger: "June 13 — quiet window, skipped nudge.")*

---

## Example 4: Routing to the Coach instead of a content skill

**User Input**: "I keep opening this and then closing it. I don't know why."

**Skill Response**:

> That's not a content problem — it's resistance, and it's normal at this stage. Let me hand
> you to the **Coach** rather than push you into another recall session.
>
> *(Routes to `memoir-coach`; does not start Recall.)*

---

## Example 5: Reconciling a stale ledger

**Situation**: `project_state.md` says "0 chapters drafted" but `chapters/` contains
`chapter_1_the-last-summer.md`.

**Skill Response**:

> Quick correction: the ledger was behind. I found Chapter 1 already drafted on disk, so
> I've updated the board to reflect it. We're further along than the notes said — nice.

*(Trusts the files, rewrites the Chapter board, then proceeds.)*
