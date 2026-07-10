# Roadmap

Where this project is going: from a set of memoir-writing skills to a **self-driving,
caring memoir companion** that runs on any mainstream agent runtime.

Guiding idea for the next phases:

> **From "docs + one-shot cron" to "contract-as-code + stateful, caring drive".**
> Adapters become pluggable code, deployment becomes one command, and the agent becomes
> a persistent loop that hears replies, adapts its pace to the writer, and enforces the
> safety floor at the tool-permission level — not just in prompt text.

## Status

| Phase | Scope | Status |
|-------|-------|--------|
| 0.a | Core skills (Recall / Architect / Writer / Reviser) + ethics & Phase 0 docs | ✅ shipped |
| 0.b | Driving layer (Orchestrator + Coach) + `project_state.md` ledger | ✅ shipped |
| 0.c | Runtime-agnostic deployment docs (capability contract, adapters, detector) | ✅ shipped |
| 0.d | Project engineering (CI, validator, governance docs) | ✅ shipped |
| 1 | Contract-as-code + real installer | 🔜 next |
| 2 | Stateful driver + structured state | planned |
| 3 | Caring adaptive drive | planned |
| 4 | Voice-first capture | planned |
| 5 | Quality & trust loop (evals + CI extensions) | planned |
| 6 | Packaging & distribution | planned |

## Phase 1 — Contract-as-code + real installer

Today's adapters are prose and the detector only prints advice. Turn the capability
contract (C1–C4) into a real interface, and detection into installation.

- A small `memoir` CLI: `detect` / `init` / `install` / `schedule` / `doctor` —
  idempotent, end-to-end setup of one runtime: install skills to the right location,
  scaffold the workspace, generate real crontab/launchd/systemd units (or
  `openclaw cron` jobs), configure the notifier with secrets stored safely.
- Adapter interface each runtime implements:
  `install_skills(bundle, workspace)` · `state_store()` · `schedule(jobs[])` ·
  `notify(msg, target)` · `run(prompt, mode, tools)`.
- Reference implementation first (Claude Code — locally testable), designed so the
  OpenClaw and Agent SDK adapters plug into the same interface.

## Phase 2 — Stateful driver + structured state

Replace the stateless one-shot cron call with a driver that holds the loop together.

- Handles both scheduled ticks **and** the writer's replies (two-way loop), with
  session continuity across days.
- **Safety enforced at the tool-permission layer**: autonomous mode gets a toolset
  that can write `memories/` but cannot touch `chapters/` — the truth contract becomes
  a mechanism, not just an instruction.
- Retries/backoff, structured logs, error surfacing.
- State upgraded to `project_state.json` (machine truth, schema-validated, atomic
  writes) rendered to `project_state.md` (human view).

## Phase 3 — Caring adaptive drive

The "主导推动" (drive-me) behaviour grows judgement instead of a fixed cron beat.

- Adaptive scheduling from response signals: did the writer reply? how short? how many
  consecutive misses? plus the Coach's resistance model.
- Quiet windows and care notes enforced **in code** (the scheduler itself skips), not
  only in prompt text.
- Automatic cadence up/down-shifting with a hard floor: never escalate pressure on a
  flagged topic; back off rather than badger.

## Phase 4 — Voice-first capture

For memoirs — especially with older writers — speaking beats typing.

- Voice-note transcription as a first-class Recall input (channel-side).
- Photo-anchored recall ("tell me about this picture").
- Optionally interview-style calls driven by the recall question sets.

## Phase 5 — Quality & trust loop

The confidence to hand your life story to an agent comes from tests.

- CI extensions: skill linting stays; add state-schema validation and adapter matrix
  smoke runs.
- Evals: a truth-contract linter (flag invented concrete details), golden-conversation
  regressions for Orchestrator routing, LLM-judge rubrics for restraint/fairness of
  generated prose.

## Phase 6 — Packaging & distribution

One source, three installs:

- OpenClaw **ClawHub** package · Claude Code **plugin** (marketplace) · **pip/npm**
  package for the SDK route.
- Semantic versioning + this changelog; the skill bundle becomes the versioned artifact.

## Cross-cutting — security & privacy hardening (spans 1/2/4)

Secret management, PII-aware channel layer (sensitive recall stays local; channels get
prompts and nudges only), optional workspace encryption at rest, and an audit log of
autonomous actions. See `SECURITY.md`.
