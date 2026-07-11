# Adapter: Claude Agent SDK

> Part of the runtime-agnostic [deployment layer](../README.md). Maps the four host
> capabilities ([contract](../capability-contract.md)) onto the
> [Claude Agent SDK](https://docs.claude.com/en/api/agent-sdk) (Python or TypeScript). This
> is the **build-it-yourself** option: most flexible, but you own the loop, the scheduler,
> and the channel. Use it when you want the agent embedded in your own service.

## C1 — workspace (files)
Point the SDK's file tools (or your own) at a workspace directory holding the data model
(`memories/`, `chapters/`, `chapter_outline.md`, `memories/style_guide.md`,
`project_state.md`). The SDK ships file-system tools; grant them to the agent scoped to that
directory.

## C2 — skills
The SDK composes the system prompt, so load the skills by reading their `SKILL.md` bodies and
concatenating them (plus `orchestration.md` and `memoir-ethics-and-care.md`) into the system
prompt — or load only the skill the Orchestrator routes to, to save tokens (progressive
disclosure). Define real tools (`read_file`/`write_file`/`list_directory` equivalents) and
map the skills' abstract `allowed-tools` to them.

## C3 + C4 — schedule and notify (the "drive me" part)
You write a single entrypoint and trigger it on a schedule; it sends the result to a channel.
Sketch (Python, illustrative):

```python
# run_nudge.py — fired by OS cron / APScheduler / a worker
from claude_agent_sdk import query, ClaudeAgentOptions   # API names may vary by version

SKILLS = load_skill_bodies("skills/")        # C2: read SKILL.md files
WORKSPACE = "/home/me/memoir"                 # C1

async def daily_nudge():
    prompt = ("Run memoir-orchestrator in AUTONOMOUS mode against this workspace: "
              "read project_state.md, honour Care notes, output ONE 15-minute task "
              "plus a reply hook. Do NOT write or finalize prose.")
    opts = ClaudeAgentOptions(
        model="<a current Claude model, e.g. Opus 4.x>",
        system_prompt=SKILLS,
        cwd=WORKSPACE,
        allowed_tools=["Read", "Write", "Glob"],   # write memory files, not final chapters
    )
    text = await collect(query(prompt=prompt, options=opts))
    send_to_channel(text)                     # C4: Telegram/Slack/email/push — your call
```

- **C3**: schedule `daily_nudge()` (and a weekly review) with the OS scheduler, a long-running
  process + `APScheduler`/`node-cron`, or your job queue.
- **C4**: `send_to_channel` is any API — Telegram Bot `sendMessage`, Slack SDK, SMTP, web
  push. The agent doesn't care which.

## Two-way + memory
Wire inbound messages (a webhook from your chat provider) to call `query()` with the writer's
text as input — that gives you the full conversational loop. The SDK's session/memory features
are a convenience layered *on top of* `project_state.md`, which remains the source of truth so
the project survives a process restart.

## Keep the safety rules
Port the care gate, quiet windows, and the no-finalize-on-schedule rule verbatim from
`memoir-orchestrator/SKILL.md`. Enforce the last one structurally too: in autonomous runs
grant tools that can write `memories/` but not overwrite `chapters/` without a human-in-the-loop
confirmation step.
