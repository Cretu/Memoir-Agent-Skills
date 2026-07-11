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
| 1 | Contract-as-code + real installer | ✅ shipped (`memoir_cli/` + `bin/memoir`; reference runtime: Claude Code) |
| 2 | Stateful driver + structured state | planned |
| 3 | Caring adaptive drive | planned |
| 4 | Voice-first capture | planned |
| 5 | Quality & trust loop (evals + CI extensions) | planned |
| 6 | Packaging & distribution | planned |

## Phase 1 — Contract-as-code + real installer ✅

Shipped as `memoir_cli/` + `bin/memoir` (stdlib-only Python, unit-tested in CI):

- `memoir detect / init / install / schedule / doctor / setup` — idempotent,
  end-to-end setup: workspace scaffolding, skills installed with tool names mapped
  per the contract, real crontab/systemd/launchd artifacts (or `openclaw cron`
  registration script), notifier with secrets in a 0600 env file,
  `schedule --apply` for marker-delimited crontab merging.
- `Adapter` ABC in `memoir_cli/contract.py`: `detect` · `install_skills` ·
  `agent_command` · `schedule` · `doctor`. Implementations: **claude-code**
  (reference), **openclaw**, **generic**.
- First tool-permission-level safety enforcement: Claude Code autonomous runs get
  a settings file denying Write/Edit under `chapters/` (deepened in Phase 2).

Remaining for later phases: SDK adapter as code, richer OpenClaw automation.

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
