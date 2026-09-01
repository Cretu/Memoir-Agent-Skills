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
| 2 | Stateful driver + structured state | ✅ shipped (`memoir run` / `memoir status`) |
| 3 | Caring adaptive drive | ✅ shipped (`adaptive.py` + `care.json` + `memoir care`) |
| 4 | Voice-first capture | ✅ shipped (`memoir capture`) |
| 5 | Quality & trust loop (evals + CI extensions) | ✅ shipped (`memoir lint` + golden corpus) |
| 6 | Packaging & distribution | ✅ shipped (`pip install`, `memoir bundle`) |

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

## Phase 2 — Stateful driver + structured state ✅

Shipped as `memoir_cli/driver.py` (`memoir run` / `memoir status`):

- Every unattended turn goes through the driver instead of a bare agent call:
  **retries with exponential backoff**, per-turn timeout, structured JSONL run log
  (`.memoir/runs.jsonl`), durable loop state with **atomic writes**
  (`.memoir/driver-state.json`: last run/success, consecutive failures, last reply).
- **Two-way loop**: `memoir run --reply "<text>"` feeds the writer's answer back to
  the Orchestrator — with session continuity on Claude Code (`--continue`) and the
  same tool-permission guardrails as autonomous runs. Wire your channel's webhook
  to this command and the conversation closes the loop.
- **Quiet-hours guard in code**: `--quiet-from/--quiet-to` config; nudges inside the
  window are skipped (and logged); replies are never quiet-gated (the writer spoke
  first); `--force` overrides.
- `memoir status`: progress + loop-state dashboard (memories/chapters counts, last
  reply, per-job health, recent runs).

*Design decision vs. the original sketch*: the memoir's own state stays in
`project_state.md`, owned by the skills — that file **is** the portable invariant
that lets the book move between runtimes. The driver owns only loop mechanics in
`driver-state.json`. A schema-validated `project_state.json` mirror is deferred to
Phase 3, where the adaptive scheduler will need to *read* care notes and cadence
programmatically.

## Phase 3 — Caring adaptive drive ✅

Shipped as `memoir_cli/adaptive.py` + `memoir_cli/care.py` (+ `memoir care` CLI):

- **Signal-driven scheduling**: before each nudge the engine reads the writer's actual
  response signals — unanswered-nudge streak from the run log, last reply time — and
  decides send / hold / soften. The ladder only ever goes *down*: 3+ unanswered →
  every 2 days with a softer, smaller ask; 6+ → weekly floor. A reply resets it
  instantly. The writer's chosen cadence (`memoir care cadence`) is the ceiling;
  silence only widens the gap below it.
- **Care settings as machine-readable config** (`.memoir/care.json`): pause-until,
  quiet dates (anniversaries), base cadence — the subset of the Care notes the
  scheduler must obey mechanically, enforced in code. Corrupt file fails safe.
  Autonomous agent runs cannot modify it (no Bash).
- **One-word writer control**: replying 「暂停」/"pause" pauses nudges for 14 days
  (bilingual confirmation, no agent involved); 「继续」/"resume" — only meaningful
  while paused — resumes. Reviews honour pause/quiet dates too.
- `memoir status` shows the streak, the next-nudge decision and reason, and the care
  settings. Topic-level care notes stay narrative in `project_state.md` for the agent.

## Phase 4 — Voice-first capture ✅

Shipped as `memoir_cli/capture.py` (`memoir capture`): a voice note, a photograph,
or a quick typed line becomes raw material in `memories/inbox/`, which the agent
then shapes into a proper Memory Capture.

- **Pluggable transcription, nothing bundled**: you supply the command
  (`--transcribe-cmd 'whisper-cli -f {file} --no-timestamps'`), exactly like the
  generic adapter's agent command. No ASR service is hardcoded and nothing leaves
  the machine unless you configured it to.
- **Photo-anchored recall**: the image is copied into `memories/photos/` and linked
  from the capture; runtimes whose agent can read image files look at it directly.
- **Privacy boundary enforced**: the transcript is written locally and never sent to
  the chat channel — only the agent's short acknowledgement goes out, and the
  capture prompt says so explicitly (verified by a test asserting the transcript
  does not appear in delivered messages).
- Raw captures are flagged `Status: **raw**` and surfaced in `memoir status` until
  shaped, so nothing silently rots in the inbox.

Not done here: interview-style calls (a channel/telephony concern, not a CLI one).

## Phase 5 — Quality & trust loop ✅

The confidence to hand your life story to an agent comes from being able to check it.

- **`memoir lint` — the truth-contract linter** (`memoir_cli/lint.py`): reads the prose
  in `chapters/`, extracts the concrete claims (years, dates, ages, quantities, proper
  names, quoted dialogue) and reports the ones with no trace in `memories/`. Spelled-out
  numbers included ("sixty-four", "three weeks"). Reconstructed dialogue is its own,
  softer category — normal in memoir, but it belongs in the author's note.
  `--format json` for tooling, `--fail-on` for CI, `.memoir/lint-allow.txt` for details
  that are genuinely the writer's and simply unwritten.
- **Golden corpus + eval in CI** (`tests/fixtures/lint/`): one chapter that invents
  details and one that is faithfully grounded. CI asserts *both* directions — the
  linter must flag all six invented details and must stay completely silent on the
  well-sourced chapter. A linter that never fires is useless; one that cries wolf gets
  switched off and stops protecting anyone. `make eval` runs it locally.

Stated plainly, what this is and is not: it is a reviewer's checklist generator, not a
truth oracle. It cannot know what the writer remembers but never wrote down, so false
positives are the intended failure mode. Proper-noun detection is Latin-script only —
for CJK prose it leans on dates, numbers and dialogue.

Still open: LLM-judge rubrics for restraint and fairness of generated prose, and
golden-conversation regressions for Orchestrator routing — both need a live model, so
they belong with a runner that can call one rather than in this deterministic suite.

## Phase 6 — Packaging & distribution ✅

One source, several installs:

- **`pip install memoir-agent`** gives a `memoir` console script. The skill bundle
  travels *inside* the wheel: `scripts/stage_bundle.py` stages it as package data and
  `memoir_cli/resources.py` finds it at runtime, falling back from
  `$MEMOIR_SKILLS_DIR` → packaged bundle → repository checkout, with a clear error
  naming every place it looked. CI installs the wheel into a clean venv, `cd`s out of
  the checkout entirely, and asserts a full `setup` lands all six skills.
- **`memoir bundle --format tar|claude-plugin|openclaw`** builds the versioned
  artifact each channel wants from that one source, so they cannot drift. Every bundle
  carries a `MANIFEST.json` of sha256 checksums that `bundle.verify()` re-checks —
  tamper detection is tested, not assumed.
- **One version number** for the package, the bundles and the changelog: the repo
  validator fails the build if a released `__version__` has no CHANGELOG section.
  `RELEASING.md` documents the whole cut.

Honest caveats: the Claude Code plugin layout is *written*, not validated against the
live plugin schema — `RELEASING.md` says to run the local plugin tooling before
publishing. Publishing itself is deliberately manual: no workflow holds registry
credentials.

## Cross-cutting — security & privacy hardening (spans 1/2/4)

Secret management, PII-aware channel layer (sensitive recall stays local; channels get
prompts and nudges only), optional workspace encryption at rest, and an audit log of
autonomous actions. See `SECURITY.md`.
