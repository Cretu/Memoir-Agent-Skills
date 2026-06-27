# Adapter: OpenClaw

> Part of the runtime-agnostic [deployment layer](../README.md). This adapter shows how
> OpenClaw provides the four host capabilities ([capability contract](../capability-contract.md)):
> **C1** files · **C2** skill discovery · **C3** scheduled invocation · **C4** outbound
> notification. OpenClaw is the best out-of-the-box fit because it provides all four natively.

This guide turns the Memoir Agent Skills into a **self-driving memoir coach** on
[OpenClaw](https://openclaw.ai/) — a local, open-source personal AI assistant that runs
Claude as an autonomous agent on your own machine, with scheduled tasks, a heartbeat, and
messaging channels (Telegram, WhatsApp, Signal, Discord, Slack, iMessage).

Why OpenClaw is a natural fit:
- Its skill format **is** `SKILL.md` + YAML frontmatter — the same format this repo already
  uses, so the existing skills drop in with minimal change.
- Its **cron + heartbeat + channels** provide the proactivity these skills can't supply on
  their own — the agent can message *you* with today's task instead of waiting to be asked.
- It runs **locally**, so your memories stay on your machine (with one caveat — see Risks).

> Docs referenced: [Skills](https://docs.openclaw.ai/tools/skills) ·
> [SKILL.md format](https://github.com/openclaw/clawhub/blob/main/docs/skill-format.md) ·
> [Cron jobs](https://docs.openclaw.ai/automation/cron-jobs) ·
> [Heartbeat](https://docs.openclaw.ai/gateway/heartbeat)

---

## P0 — Install and connect a channel
1. Install OpenClaw and run the gateway (see the OpenClaw docs).
2. Connect **one** chat channel you check on your phone (Telegram is the easiest to start).
3. Pick a **workspace folder** for the book (e.g. `~/memoir/`). This is where the data files
   live: `memories/`, `chapters/`, `chapter_outline.md`, `memories/style_guide.md`, and
   `project_state.md`.

## P1 — Install the skills
OpenClaw discovers any `SKILL.md` under a configured skills root. Put the skill folders in
either location:
- `~/.openclaw/skills/<skill-name>/SKILL.md` — available across **all** OpenClaw sessions, or
- `<workspace>/skills/<skill-name>/SKILL.md` — scoped to the memoir workspace (recommended,
  keeps the book self-contained).

Copy these folders in: `memoir-purpose-and-audience` (the `.md` doc), `memoir-memory-recall`,
`memoir-architect-biographer`, `memoir-writing`, `memoir-revision`, `memoir-orchestrator`,
`memoir-coach`. Also copy the shared docs `memoir-ethics-and-care.md`,
`memoir-purpose-and-audience.md`, `orchestration.md`, and the `project_state.md` template
into the workspace so the skills can read them.

**Alignment fixes when porting** (see also the
[Skill Workshop](https://docs.openclaw.ai/tools/skill-workshop) docs):
1. **Tool names.** The `allowed-tools` in these skills use abstract names
   (`read_file`, `write_file`, `list_directory`, `text-generation`, `memory`). Map them to
   the tool names OpenClaw/Claude actually expose (file read/write/list + shell) per the
   [skill-format doc](https://github.com/openclaw/clawhub/blob/main/docs/skill-format.md).
   OpenClaw runs a security analysis over the declared permissions, so declare the real ones.
2. **Description ≤ 160 bytes.** OpenClaw caps the `description` frontmatter field at 160
   bytes. All skills in this repo now comply — keep any future edits under the limit.
3. **Support-file folders.** OpenClaw expects supplementary files under standard folders:
   `examples/`, `references/`, `scripts/`, `templates/`, `assets/`. This repo already follows
   the convention (`references/reference.md`, `examples/EXAMPLES.md`, and `templates/` for
   prompt files), so the skill folders drop in as-is.
4. **`.claude/skills.json` is not used by OpenClaw** — it discovers skills by finding
   `SKILL.md` under the skills root. You can ignore that manifest here; the folder layout is
   what matters.

## P1.5 — Author and iterate via Skill Workshop (proposal-first)
OpenClaw's [Skill Workshop](https://docs.openclaw.ai/tools/skill-workshop) is the *governed*
way to create and change workspace skills: agents and operators never write a live `SKILL.md`
directly — they create a `PROPOSAL.md`, which becomes a live skill only when explicitly
**applied** (with a scanner re-run, hash-binding, and a no-clobber check on create). Use it
two ways:
- **To install/evolve these skills**: instead of hand-copying, you can have OpenClaw
  `propose-create` each skill and `apply` it, so changes go through the same review gate.
- **To let the agent improve itself safely**: the memoir agent can *propose* refinements to
  its own skills (e.g. a better recall prompt set) as proposals you approve — useful, and it
  pairs well with the safety stance below, because nothing self-modifies without sign-off.

Keep `approvalPolicy` at its default (manual approval for `apply`/`reject`/`quarantine`)
rather than `"auto"` for a memoir project — you want a human in the loop on anything that
changes how the agent handles your life story. Note that in restrictive tool policies the
`skill_workshop` tool must be explicitly allowed.

Smoke test: start a session and ask *"Where are we with my memoir?"* — the Orchestrator
should read `project_state.md` and report the phase + next step.

## P2 — Make the Orchestrator the front door
Configure the memoir workspace so a normal session lands on `memoir-orchestrator` first. It
reads `project_state.md`, decides the phase, and routes to the specialist skill (Recall /
Architect / Writer / Reviser) or to `memoir-coach` when the blocker is motivation. It also
updates the ledger at the end of every run. Nothing else in the system is allowed to be
proactive — keep it that way.

## P3 — Schedule the proactive nudges (cron)
This is what makes it "drive" you. Cron jobs live in `~/.openclaw/cron/jobs.json` and survive
restarts. Use **isolated** runs for self-contained nudges/reports and deliver the result to
your channel.

**Daily 15-minute task** (8pm, delivered to Telegram):
```bash
openclaw cron create "0 20 * * *" \
  "Run memoir-orchestrator in autonomous mode: read project_state.md, honour the Care notes, \
   and send me ONE 15-minute memoir task plus an easy reply hook. Do not write or finalize prose." \
  --name "Daily memoir push" \
  --tz "Asia/Shanghai" \
  --session isolated \
  --announce --channel telegram --to "<your-chat-id>"
```

**Weekly review** (Sunday 7pm — progress + gentle plan for the week):
```bash
openclaw cron create "0 19 * * 0" \
  "Run memoir-orchestrator: summarize this week's progress from project_state.md, reflect the \
   chapter board back to me, and propose (not impose) next week's cadence via memoir-coach." \
  --name "Weekly memoir review" \
  --tz "Asia/Shanghai" \
  --session isolated \
  --announce --channel telegram --to "<your-chat-id>"
```

Adjust times, timezone, channel, and `--to` target to your setup. Use `--session main`
instead of `isolated` only if you want the nudge to share your live conversation context
(usually not needed for a daily task).

## P4 — Heartbeat (light follow-up)
The heartbeat is a periodic main-session turn (~every 30 min) for routine monitoring. Keep
its memoir role **light**: if you started a recall earlier and went quiet, it can gently
follow up once and lower the ask ("even one sentence is a win"). It should respect the same
Care notes and never escalate pressure. Most of the driving should come from the cron tasks
above; the heartbeat is just for not dropping a thread mid-session.

## P5 — Finishing and export
When the Chapter board is all ✅, the Orchestrator routes to closing the book:
- Draft front matter (title page, dedication, and an **author's note** assembled from
  `chapters/authors_note_flags.md`) via `memoir-revision`.
- Merge `chapters/*.md` in order and export to PDF/EPUB (e.g. with `pandoc` via OpenClaw's
  shell access).

---

## Risks to design around (read before going autonomous)
These three are baked into the Orchestrator and Coach skills; keep them intact.

### 1. Privacy — local is good, but the channel isn't fully private
Memoirs hold deeply sensitive material about you and your family. OpenClaw running locally
means the **files** stay on your machine — a real advantage. But messages through a chat
channel (WhatsApp/Telegram/etc.) **pass through that provider's servers**. Practical rule:
use the channel for *prompts, nudges, and short recall replies*; keep the most sensitive
passages in the local workspace files, not in chat history. Consider a more private channel
(e.g. Signal) if this matters to you.

### 2. Proactive nudging vs. emotional safety
Recall surfaces grief and trauma; a dumb scheduler can poke a wound at the worst moment. The
Orchestrator's **Care gate** and the Coach's resistance distinction exist to prevent this:
off-limits topics are never auto-raised, quiet windows are honoured, and observed stopping
signals slow the next session down. Never "optimize for streaks" over the writer's pace.

### 3. The truth contract is not automatable
A self-driving agent must not generate prose and save it as *your* words and memories.
Scheduled/unattended runs may **recall, organize, remind, and propose** — they may **not**
draft-as-final or alter `chapters/` without you in the loop. Keep drafting and finalizing
interactive and confirmed (see `memoir-ethics-and-care.md`, Part 3).
