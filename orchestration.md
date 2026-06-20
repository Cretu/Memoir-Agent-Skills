# Memoir Skills Orchestration

This document defines how `memoir-memory-recall`, `memoir-architect-biographer`, and `memoir-writing` are coordinated to create a complete memoir writing workflow.

## Shared Terminology

Use these canonical names and short aliases consistently across all skills and documentation:

| Canonical Name              | Short Alias | Role                        |
|-----------------------------|-------------|-----------------------------|
| memoir-memory-recall        | Recall      | Interviewer / Memory Guide  |
| memoir-architect-biographer | Architect   | Editorial Consultant        |
| memoir-writing              | Writer      | Literary Ghostwriter        |
| memoir-revision             | Reviser     | Editor                      |

## Shared References (cross-cutting, not phases)

Two documents apply across every phase rather than belonging to one skill:

| Document                       | What it governs                                              | Who reads it |
|--------------------------------|-------------------------------------------------------------|--------------|
| `memoir-purpose-and-audience.md` | **Phase 0**: reader, scope, theme → the Project Compass    | Architect (owns it); any skill if unset |
| `memoir-ethics-and-care.md`      | Emotional safety, writing about real people, truth contract | All skills, each phase |

## File Contracts

Each skill has a defined set of files it reads and writes. Use this as a reference when starting mid-workflow:

| Skill      | Reads From                                                                 | Writes To                        |
|------------|----------------------------------------------------------------------------|----------------------------------|
| Recall     | `memoir-ethics-and-care.md`                                                | `memories/[title].md`            |
| Architect  | `memories/*.md`, `memoir-purpose-and-audience.md`, `memoir-ethics-and-care.md` | `chapter_outline.md`         |
|            |                                                                            | `memories/style_guide.md` (Compass + style) |
| Writer     | `chapter_outline.md`, `memories/style_guide.md`, `memories/[relevant].md`, `memoir-ethics-and-care.md` | `chapters/chapter_[N]_[slug].md` |
| Reviser    | `chapters/*.md`, `chapter_outline.md`, `memories/style_guide.md`, `memoir-ethics-and-care.md` | `chapters/chapter_[N]_[slug].md` (revised), `chapters/authors_note_flags.md` |

## Overview

The skills form a sequential pipeline, opened by a one-time **Phase 0** (Purpose &
Audience) and closed by a **Phase 4** (Revision):

```
        Phase 0: Purpose & Audience  (set the Project Compass)
                        │
                        ▼
┌─────────────────┐    ┌─────────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Memory Recall  │ →  │  Architect/Biographer│ →  │  Memoir Writing │ →  │ Memoir Revision │
│  (extract)      │    │  (structure)        │    │  (craft)        │    │  (edit + check) │
└─────────────────┘    └─────────────────────┘    └─────────────────┘    └─────────────────┘
        ▲                                                                          │
        └──────────────── iterate: new material, restructure, rewrite ────────────┘

   Cross-cutting throughout: memoir-ethics-and-care.md (safety, real people, truth)
```

## Phase 0: Purpose & Audience

**Doc**: `memoir-purpose-and-audience.md` (run by the Architect, or any skill if the writer arrives cold)

**Goal**: Decide *who this is for* and *what it's about* before recalling in earnest.

**What it does**:
- Establishes the reader (family / public / self) — which sets the legal and tonal bar.
- Sets scope (whole-life / single thread / vignettes) — recommends focused over comprehensive.
- Names a working theme (the "so what").

**Output**: A **Project Compass** block at the top of `memories/style_guide.md`.

**When to use**: Once, at the start. Revisit when the theme clarifies after recall.

## Phase 1: Memory Recall

**Skill**: `memoir-memory-recall`

**Goal**: Extract raw memories with sensory detail and emotional context.

**What it does**:
- Guides user through structured recall questions
- Documents specific moments, people, places
- Preserves details without interpretation
- Builds a memory inventory

**Output**: Raw memory notes with context, sensory details, and emotional notes

**When to use**:
- User wants to explore a specific time period
- User has fragmented memories to organize
- User needs help triggering deeper recall

## Phase 2: Structure Design

**Skill**: `memoir-architect-biographer`

**Goal**: Transform raw memories into a coherent memoir structure.

**What it does**:
- Identifies thematic threads across memories
- Creates chapter outlines with clear purposes
- Validates timeline consistency
- Ensures emotional arc coherence

**Output**: Chapter outline with themes, time periods, and key moments

**When to use**:
- After sufficient memories have been recalled
- User needs help organizing scattered memories
- User is ready to think about book structure

## Phase 3: Writing

**Skill**: `memoir-writing`

**Goal**: Craft raw memories and approved structure into literary prose.

**What it does**:
- Transforms bullet-point memories into scenes
- Applies restrained memoir voice
- Balances scene, action, and aftermath
- Maintains consistent tone throughout

**Output**: Polished prose chapters

**When to use**:
- Memory recall is complete
- Structure has been approved
- User wants to see memories as written passages

## Phase 4: Revision

**Skill**: `memoir-revision`

**Goal**: Make drafted chapters better and safer — without overwriting the writer's voice.

**What it does**:
- Runs ordered passes: developmental → line → continuity → responsibility.
- Checks the draft against its Project Compass and the truth/fairness/safety standards in
  `memoir-ethics-and-care.md`.
- Collects disclosures (changed names, composites, compressed timelines) for an author's note.

**Output**: Revised `chapters/*.md` and `chapters/authors_note_flags.md`; eventually front matter.

**When to use**: After a chapter is drafted, and as a final pass before the memoir is "done."

## Coordination Patterns

### Linear Pipeline (Recommended)
For users starting from scratch:

0. Set the **Project Compass** (`memoir-purpose-and-audience.md`) — reader, scope, theme
1. Use `memoir-memory-recall` to explore key periods
2. Use `memoir-architect-biographer` to organize findings
3. Use `memoir-writing` to draft chapters
4. Use `memoir-revision` to edit and run the responsibility check

### Iterative Mode
For refinement within a chapter:

1. Recall more details about specific moments
2. Update structure if needed
3. Rewrite passage with new details

### Parallel Exploration
For non-linear approaches:

1. Recall memories for multiple chapters simultaneously
2. Periodically use `memoir-architect-biographer` to reorganize
3. Write completed chapters as ready

## Data Flow

```
User Input
    │
    ▼
┌───────────────────┐
│ Phase 0: Compass  │  →  memories/style_guide.md (Project Compass)
└───────────────────┘
    │
    ▼
┌───────────────────┐
│ Memory Recall     │  →  memories/[title].md (Markdown)
└───────────────────┘
    │
    ▼
┌───────────────────┐
│ Architect/Bio     │  →  chapter_outline.md (Markdown)
└───────────────────┘
    │
    ▼
┌───────────────────┐
│ Writing           │  →  chapters/[title].md (Markdown)
└───────────────────┘
    │
    ▼
┌───────────────────┐
│ Revision          │  →  chapters/[title].md (revised) + authors_note_flags.md
└───────────────────┘
```

## File Management Strategy (Context Control)

To prevent context window overflow and ensure consistency:

1.  **Atomic Memory Files**: `memoir-memory-recall` saves output into separate files in `memories/`.
2.  **Style Calibration**: `memoir-writing` refers to `memories/style_guide.md` for voice consistency.
3.  **Selective Context Loading**: When running `memoir-writing`:
    *   Load the **`chapter_outline.md`** (for global context).
    *   Load the **`memories/style_guide.md`** (for tone).
    *   Load **ONLY** the specific `memories/*.md` files relevant to the current chapter.

## Execution Modes

### 🚀 Quick Start (Linear)
Best for users who want to see results fast.
1.  Recall **one** specific, vivid memory (10 mins).
2.  Skip the full biography outline.
3.  Write a **single standalone vignette** based on that memory.

### 🏗️ Deep Architect (Holistic)
Best for users committed to a full book.
1.  Spend multiple sessions purely on Recall across different life eras.
2.  Build a comprehensive Outline.
3.  Write chapters systematically.

## Transition Guidelines

### Between Recall and Architecture
- Confirm user has explored key life periods
- Ensure enough raw material exists for chapters
- Ask: "What period feels most important to start with?"

### Between Architecture and Writing
- Review and approve chapter outline
- Confirm which chapter to write first
- Select specific memories for each chapter

### Within Any Phase
- User can return to earlier phases at any time
- Memories can be added to any chapter
- Structure can be revised as new memories emerge

## Best Practices

1. **Don't rush phases**: Each phase serves a distinct purpose
2. **Document everything**: Raw memories inform all later work
3. **Stay in phase**: Writing skill should not do recalling
4. **Iterate freely**: Return to earlier phases as needed
5. **Trust the process**: Each phase builds on the previous
6. **Compass before content**: Don't recall in earnest until reader, scope, and theme are set
7. **Safety over completeness**: A memory the writer isn't ready for can wait; never push deeper into trauma (see `memoir-ethics-and-care.md`, Part 1)
8. **Drafts aren't done**: A first draft is clay on the wheel — Revision is where the book is made
