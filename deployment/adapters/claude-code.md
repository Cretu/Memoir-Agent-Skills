# Adapter: Claude Code

> Part of the runtime-agnostic [deployment layer](../README.md). Maps the four host
> capabilities ([contract](../capability-contract.md)) onto Anthropic's
> [Claude Code](https://claude.com/claude-code) CLI. Closest to this repo's native format —
> the skills are already `SKILL.md`. Claude Code has no built-in scheduler, so **C3/C4 come
> from the OS** (cron/launchd/systemd + a notifier).

## C1 — workspace (files)
Claude Code operates in its current working directory. Pick a workspace and keep the data
model there:
```
~/memoir/
├── memories/        chapters/        chapter_outline.md
├── memories/style_guide.md          project_state.md
```
File ops are native (`Read`, `Write`, `Edit`, `Glob`, `LS`, `Bash`). No setup needed.

## C2 — skill discovery
Claude Code discovers skills at:
- **Project**: `<workspace>/.claude/skills/<name>/SKILL.md` (recommended — keeps the book self-contained), or
- **User**: `~/.claude/skills/<name>/SKILL.md` (available everywhere).

Copy the seven skill folders there (`memoir-orchestrator`, `memoir-coach`,
`memoir-memory-recall`, `memoir-architect-biographer`, `memoir-writing`, `memoir-revision`,
plus the `memoir-purpose-and-audience.md` doc), and copy the shared docs
(`memoir-ethics-and-care.md`, `orchestration.md`) and the `project_state.md` template into
the workspace.

**Tool-name mapping** (see the contract's table): set each skill's `allowed-tools` to real
Claude Code tools — `read_file→Read`, `write_file→Write`/`Edit`, `list_directory→Glob`/`LS`;
drop `text-generation`/`memory` (implicit; state lives in workspace files). Keep
`description` short — Claude Code uses it for auto-trigger.

## C3 + C4 — schedule and notify (the "drive me" part)
Claude Code runs **headless** with `claude -p "<prompt>"`. Combine an OS scheduler (C3) with
a pipe to a notifier (C4). Example daily 8pm nudge via `cron`, delivered through
[ntfy.sh](https://ntfy.sh):

```cron
# crontab -e
0 20 * * * cd "$HOME/memoir" && claude -p "Run the memoir-orchestrator skill in autonomous \
mode: read project_state.md, honour the Care notes, and output ONE 15-minute memoir task \
plus an easy reply hook. Do NOT write or finalize prose." \
--allowedTools "Read,Write,Edit,Glob,Bash" \
2>>"$HOME/memoir/.cron.log" | curl -s -d @- ntfy.sh/<your-topic> >/dev/null
```

Weekly review — same shape, Sundays 7pm, prompt asks for a progress summary + a proposed
cadence via `memoir-coach`. Swap the notifier for a Telegram bot, email, or Slack webhook
(see [generic-cron.md](generic-cron.md) for C4 one-liners and C3 launchd/systemd variants).

**Two-way replies** (optional): plain cron is push-only. For a reply loop, point a small
webhook (or a chat bot) at `claude -p` so the writer's message becomes the next session's
input — at which point you're approaching what OpenClaw gives you natively.

## Semi-auto without any scheduler
Skip C3/C4 entirely and use a **SessionStart hook** that runs the Orchestrator each time you
open Claude Code in the workspace — it greets you with where you are and the next step. You
open the sessions; it still drives them.

## Keep the safety rules
The care gate, quiet windows, and "scheduled runs never finalize prose" live in
`memoir-orchestrator/SKILL.md` — they apply unchanged here. The `--allowedTools` above
deliberately permits writing *memory* files but the prompt forbids finalizing chapters; keep
that split.
