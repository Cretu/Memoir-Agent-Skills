# Adapter: Generic (cron + CLI)

> Part of the runtime-agnostic [deployment layer](../README.md). The fallback for **any**
> runtime that exposes a command-line entrypoint. If your agent CLI can take an instruction
> and read/write files in a directory, this adapter gives it C3 (schedule) and C4 (notify)
> from the operating system. Use the C-by-C pieces below à la carte.

Throughout, `AGENT_RUN` is *your* agent's headless invocation, e.g.
`claude -p "..."`, `openclaw run "..."`, or `your-cli --once "..."`.

## C1 — workspace
Any directory with the data model (`memories/`, `chapters/`, `chapter_outline.md`,
`memories/style_guide.md`, `project_state.md`). The agent must be able to read/write it.

## C2 — skills
However your runtime ingests instructions: a skills folder it scans, an `--include` flag, or
(lowest common denominator) concatenate the `SKILL.md` bodies into the system prompt. Map the
abstract `allowed-tools` to your runtime's real file tools (see the contract's mapping table).

## C3 — schedule (pick one)
**Linux/cron:**
```cron
0 20 * * * cd /home/me/memoir && AGENT_RUN "Run memoir-orchestrator autonomous mode: one 15-min task, no prose." | /home/me/memoir/notify.sh
```
**macOS/launchd** — `~/Library/LaunchAgents/com.me.memoir.plist` running the same command via
`ProgramArguments` with a `StartCalendarInterval` of `{Hour=20; Minute=0;}`, then
`launchctl load` it.
**systemd timer** — a `memoir-nudge.service` (`ExecStart=` the command) paired with a
`memoir-nudge.timer` (`OnCalendar=*-*-* 20:00:00`), then `systemctl --user enable --now
memoir-nudge.timer`.

## C4 — notify (pick one; this is `notify.sh`)
Read the agent's text from stdin and push it to where the writer looks:
```sh
# ntfy.sh (simplest)
curl -s -d @- ntfy.sh/<your-topic> >/dev/null

# Telegram bot
read -r MSG; curl -s "https://api.telegram.org/bot<TOKEN>/sendMessage" \
  --data-urlencode "chat_id=<CHAT_ID>" --data-urlencode "text=$MSG" >/dev/null

# Slack incoming webhook
read -r MSG; curl -s -X POST -H 'Content-type: application/json' \
  -d "{\"text\":\"$MSG\"}" "<SLACK_WEBHOOK_URL>" >/dev/null

# Email
mail -s "Today's memoir task" me@example.com
```
> Privacy: webhooks/bots route through a third party. Keep sensitive recall in the local
> workspace files; use the channel for short prompts and nudges (see openclaw.md → Risks).

## C3+C4 together (daily + weekly)
```cron
0 20 * * *  cd /home/me/memoir && AGENT_RUN "memoir-orchestrator autonomous: ONE 15-min task + reply hook; no prose." | /home/me/memoir/notify.sh
0 19 * * 0  cd /home/me/memoir && AGENT_RUN "memoir-orchestrator: weekly progress summary + propose a cadence via memoir-coach." | /home/me/memoir/notify.sh
```

## Keep the safety rules
The care gate, quiet windows, and "no finalizing prose on a schedule" are in the skills, not
the cron line — they hold as long as you ported the skill text. Don't add a job that writes
`chapters/` unattended.
