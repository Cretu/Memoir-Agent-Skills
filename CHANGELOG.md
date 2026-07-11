# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- **Stateful driver** (`memoir run` / `memoir status`, ROADMAP Phase 2):
  scheduled turns get retries with backoff, timeouts, a JSONL run log, and
  durable loop state with atomic writes; a two-way loop via
  `memoir run --reply` (session continuity on Claude Code, same guardrails);
  a code-level quiet-hours guard (replies are never quiet-gated); and a
  progress/health dashboard. Cron and systemd artifacts now invoke the driver
  instead of bare agent calls.
- **`memoir` CLI** (`memoir_cli/` + `bin/memoir`, ROADMAP Phase 1): the
  capability contract as code. `detect / init / install / schedule / doctor /
  setup` with adapters for claude-code (reference), openclaw, and generic
  cron+CLI. Installs skills with tool-name mapping, scaffolds the workspace,
  generates cron/systemd/launchd artifacts, configures notifiers (ntfy /
  Telegram / Slack / file) with secrets in a 0600 env file, and enforces the
  truth contract at the tool-permission layer on Claude Code (autonomous runs
  cannot write `chapters/`). Unit-tested + e2e-smoked in CI.
- **Runtime-agnostic deployment layer** (`deployment/`): the four-capability
  contract (C1 files · C2 skills · C3 schedule · C4 notify), per-runtime
  adapters (OpenClaw, Claude Code, Claude Agent SDK, generic cron+CLI, other
  frameworks), and a read-only `detect-runtime.sh` that probes the host and
  recommends an adapter.
- **Project engineering**: CI (skill/link/layout validation, ShellCheck,
  detector smoke run), `scripts/validate.py`, `Makefile`, LICENSE, CHANGELOG,
  CONTRIBUTING, SECURITY, ROADMAP, issue/PR templates, `.editorconfig`.

### Changed
- Orchestrator/Coach wording generalized from hardcoded "cron/heartbeat" to
  "the host scheduler (see `deployment/`)".

## [0.4.0] — 2026-06-20

### Added
- **Driving layer**: `memoir-orchestrator` (project lead: phase detection, the
  single next action, routing, proactive scheduled nudges with a care gate and
  truth-contract guardrails) and `memoir-coach` (pacing, resistance,
  sustainable cadence, milestones).
- `project_state.md` progress ledger (snapshot, chapter board, care notes).
- OpenClaw deployment guide (later generalized into `deployment/`).

### Changed
- All skills aligned with OpenClaw conventions: descriptions ≤160 bytes,
  support files under `references/`, `examples/`, `templates/`.

## [0.3.0] — 2026-06-20

### Added
- `memoir-revision` skill: ordered passes (developmental → line → continuity →
  responsibility).
- `memoir-ethics-and-care.md`: emotional safety, writing about real people,
  the truth contract.
- `memoir-purpose-and-audience.md` (Phase 0): reader, scope, theme — the
  Project Compass.

## [0.2.0] — 2026-06-11

### Changed
- Cross-skill coherence: unified naming, file contracts, phase transitions.

## [0.1.0] — 2026-02-01

### Added
- Initial skills: `memoir-memory-recall`, `memoir-architect-biographer`,
  `memoir-writing`, plus `orchestration.md` and the memories/chapters data
  model.
