# Deploying the memoir agent (any runtime)

The memoir skills are portable markdown. The **driving layer** (Orchestrator + Coach) needs
just four host capabilities — see the **[capability contract](capability-contract.md)**. This
folder makes the agent runtime-generic: one contract, one [adapter](adapters/) per runtime,
and a detection script that tells you which adapter you're on.

```
your runtime ──provides──▶ C1 files · C2 skills · C3 schedule · C4 notify
                              │
              the same skills + project_state.md run on top, unchanged
```

## Quick start
1. **Detect your environment**: `sh deployment/detect-runtime.sh`
   It reports which runtimes and schedulers are present and points you at an adapter.
2. **Open the matching [adapter](adapters/)** and wire up C1–C4.
3. **Smoke-test**: start a session and ask *"Where are we with my memoir?"* — the
   Orchestrator should read `project_state.md` and name the single next step.
4. **Go proactive**: register the daily-task and weekly-review schedule from the adapter.

## Adapter matrix

| Runtime | C1 files | C2 skills | C3 schedule | C4 notify | Adapter |
|---------|----------|-----------|-------------|-----------|---------|
| **OpenClaw** | workspace | `~/.openclaw/skills/` or workspace `skills/` | native cron + heartbeat | native channels (WhatsApp/TG/Signal/…) | [openclaw.md](adapters/openclaw.md) |
| **Claude Code** | working dir | `.claude/skills/<name>/SKILL.md` | OS cron → headless `claude -p` | pipe output → notifier | [claude-code.md](adapters/claude-code.md) |
| **Claude Agent SDK** | your filesystem | load `SKILL.md` text in system prompt | your loop + OS cron | your code (any API) | [claude-agent-sdk.md](adapters/claude-agent-sdk.md) |
| **Generic (cron + CLI)** | any directory | however the CLI takes instructions | crontab / launchd / systemd | ntfy / webhook / mail | [generic-cron.md](adapters/generic-cron.md) |
| **Other frameworks** | varies (often native) | prompts/nodes | built-in trigger | messaging node | [other-frameworks.md](adapters/other-frameworks.md) |

Legend: **C1** file read/write · **C2** skill discovery · **C3** scheduled run · **C4** outbound message.

## When a capability is missing — graceful degradation
- **No C3/C4** → run **semi-auto**: you open each session; the Orchestrator still tracks
  state and drives *within* the session. You lose only the unattended push, not the project
  management.
- **No C2** → paste the skill bodies into the system prompt; everything else works.
- **No C1** → not supported; the workspace files are the agent's memory.

## Don't lose these when porting
The safety guarantees live in the **skills**, not the host — the Orchestrator's **care gate**,
**quiet windows**, and the **truth-contract** rule that *a scheduled run never finalizes prose*
(it may recall/organize/remind/propose only). Keep them intact on every runtime
(see `memoir-ethics-and-care.md` and `memoir-orchestrator/SKILL.md`).
