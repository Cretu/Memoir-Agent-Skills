"""memoir — one-command setup for the memoir agent.

    memoir detect  [--json]
    memoir init     --workspace PATH
    memoir install  --workspace PATH [--adapter ID]
    memoir schedule --workspace PATH [--adapter ID] [times] [--notify ...] [--apply]
    memoir doctor   --workspace PATH [--adapter ID]
    memoir setup    --workspace PATH [...]   # init + install + schedule
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__, capture as capture_mod, care as care_mod
from . import detect as detect_mod, driver as driver_mod, lint as lint_mod
from . import notify as notify_mod, workspace as ws_mod
from .adapters import ADAPTERS, auto_pick, get_adapter
from .adapters.claude_code import ClaudeCodeAdapter
from .adapters.generic import GenericCronAdapter
from .adapters.openclaw import OpenClawAdapter
from .jobs import standard_jobs

REPO = Path(__file__).resolve().parents[1]


def _adapter_from(args) -> object:
    if getattr(args, "adapter", None):
        adapter = get_adapter(args.adapter)
    else:
        adapter = auto_pick()
        print(f"(auto-selected adapter: {adapter.id})")
    if isinstance(adapter, GenericCronAdapter) and getattr(args, "agent_cmd", ""):
        adapter.agent_cmd = args.agent_cmd
    if isinstance(adapter, OpenClawAdapter):
        if getattr(args, "channel", None):
            adapter.channel = args.channel
        if getattr(args, "to", None):
            adapter.to = args.to
    return adapter


def cmd_detect(args) -> int:
    ws = Path(args.workspace).expanduser() if args.workspace else None
    report = detect_mod.probe(ws)
    print(json.dumps(report, indent=2) if args.json else detect_mod.render(report))
    return 0


def cmd_init(args) -> int:
    ws = Path(args.workspace).expanduser()
    created = ws_mod.init(REPO, ws)
    if created:
        print(f"initialized {ws}:")
        for c in created:
            print(f"  + {c}")
    else:
        print(f"{ws} already initialized (nothing to do)")
    return 0


def cmd_install(args) -> int:
    ws = Path(args.workspace).expanduser()
    adapter = _adapter_from(args)
    installed = adapter.install_skills(REPO, ws)
    print(f"installed {len(installed)} skills for {adapter.id}:")
    for name in installed:
        print(f"  + {name}")
    return 0


def cmd_schedule(args) -> int:
    ws = Path(args.workspace).expanduser()
    adapter = _adapter_from(args)
    jobs = standard_jobs(args.daily_time, args.weekly_day, args.weekly_time)

    notify_cmd = ""
    if not isinstance(adapter, OpenClawAdapter):  # OpenClaw delivers natively (C4)
        script = notify_mod.write_notifier(
            ws,
            args.notify,
            {
                "ntfy_topic": args.ntfy_topic,
                "telegram_token": args.telegram_token,
                "telegram_chat": args.telegram_chat,
                "slack_webhook": args.slack_webhook,
            },
        )
        notify_cmd = str(script)
        print(f"notifier: {args.notify} -> {script}")

    artifacts, instructions = adapter.schedule(ws, jobs, notify_cmd)

    # persist driver config (adapter choice + quiet hours) for `memoir run`
    cfg = driver_mod.load_config(ws)
    cfg["adapter"] = adapter.id
    if getattr(args, "agent_cmd", ""):
        cfg["agent_cmd"] = args.agent_cmd
    cfg["quiet_from"] = args.quiet_from
    cfg["quiet_to"] = args.quiet_to
    if getattr(args, "transcribe_cmd", ""):
        cfg["transcribe_cmd"] = args.transcribe_cmd
    driver_mod.save_config(ws, cfg)

    print("artifacts:")
    for a in artifacts:
        print(f"  + {a}")
    print(instructions)

    if args.apply:
        if isinstance(adapter, ClaudeCodeAdapter):
            print(adapter.apply_cron(ws))
        else:
            print(f"--apply is not supported for {adapter.id}; follow the instructions above")
    return 0


def cmd_doctor(args) -> int:
    ws = Path(args.workspace).expanduser()
    adapter = _adapter_from(args)
    checks = ws_mod.doctor(ws) + adapter.doctor(REPO, ws)
    failed = 0
    for c in checks:
        mark = "ok " if c.ok else "FAIL"
        line = f"  [{mark}] {c.name}"
        if c.detail:
            line += f" — {c.detail}"
        print(line)
        if not c.ok:
            failed += 1
            if c.fix:
                print(f"         fix: {c.fix}")
    print(f"doctor: {len(checks) - failed}/{len(checks)} checks passed")
    return 1 if failed else 0


def cmd_run(args) -> int:
    ws = Path(args.workspace).expanduser()
    if args.reply:
        result = driver_mod.run_reply(
            ws, args.reply,
            attempts=args.attempts, retry_delay=args.retry_delay, timeout=args.timeout,
        )
    else:
        result = driver_mod.run_job(
            ws, args.job,
            attempts=args.attempts, retry_delay=args.retry_delay,
            timeout=args.timeout, force=args.force,
        )
    if result.output:
        print(result.output)
    if not result.ok:
        print(f"run failed after {result.attempts} attempt(s): {result.error}",
              file=sys.stderr)
    return 0 if result.ok else 1


def cmd_status(args) -> int:
    print(driver_mod.status(Path(args.workspace).expanduser(), tail=args.tail))
    return 0


def cmd_capture(args) -> int:
    ws = Path(args.workspace).expanduser()
    run_agent = not args.no_agent
    if args.text:
        result = capture_mod.capture_text(ws, args.text, run_agent=run_agent,
                                          timeout=args.timeout)
    else:
        src = Path(args.file).expanduser() if args.file else None
        kind = args.kind
        if kind == "auto":
            kind = capture_mod.guess_kind(src)
            if kind == "unknown":
                raise SystemExit(
                    f"cannot tell whether {src.name} is audio or a photo — "
                    "pass --kind audio|photo"
                )
        if kind == "audio":
            result = capture_mod.capture_voice(
                ws, src, run_agent=run_agent,
                transcribe_timeout=args.transcribe_timeout, timeout=args.timeout,
            )
        else:
            result = capture_mod.capture_photo(
                ws, src, note=args.note, run_agent=run_agent, timeout=args.timeout
            )

    print(f"captured -> {result.path.relative_to(ws)}")
    if result.asset:
        print(f"photo    -> {result.asset.relative_to(ws)}")
    preview = result.text.strip().splitlines()[0][:80] if result.text.strip() else ""
    if preview:
        print(f"first line: {preview}")
    if result.agent_ran:
        if result.agent_output.strip():
            print("\n" + result.agent_output.strip())
        print(f"(delivered to the writer: {'yes' if result.delivered else 'no'})")
    else:
        print("(agent not run — shape it in your next session)")
    return 0


def cmd_lint(args) -> int:
    ws = Path(args.workspace).expanduser()
    findings = lint_mod.lint_workspace(
        ws,
        chapters_dir=Path(args.chapters).expanduser() if args.chapters else None,
        memories_dir=Path(args.memories).expanduser() if args.memories else None,
    )
    print(lint_mod.render(findings, as_json=args.format == "json"))
    if args.fail_on == "never":
        return 0
    if args.fail_on == "any":
        return 1 if findings else 0
    return 1 if any(f.kind == lint_mod.KIND_UNSUPPORTED for f in findings) else 0


def cmd_care(args) -> int:
    import datetime as dt

    ws = Path(args.workspace).expanduser()
    if args.care_action == "show":
        print(care_mod.render(care_mod.load(ws), dt.date.today()))
    elif args.care_action == "pause":
        until = (
            dt.date.fromisoformat(args.until) if args.until
            else dt.date.today() + dt.timedelta(days=args.days)
        )
        care_mod.set_pause(ws, until)
        print(f"paused until {until.isoformat()} — no nudges before then")
    elif args.care_action == "resume":
        care_mod.clear_pause(ws)
        print("resumed — nudges follow the usual cadence again")
    elif args.care_action == "quiet":
        care_mod.add_quiet_dates(ws, args.date_from, args.date_to or args.date_from,
                                 args.reason)
        print(f"quiet dates added: {args.date_from} → {args.date_to or args.date_from}")
    elif args.care_action == "cadence":
        care_mod.set_cadence(ws, args.per_week)
        print(f"cadence set: {args.per_week} nudge(s)/week")
    return 0


def cmd_setup(args) -> int:
    rc = cmd_init(args)
    rc = rc or cmd_install(args)
    rc = rc or cmd_schedule(args)
    if rc == 0:
        print("\nsetup complete — verify with: memoir doctor --workspace", args.workspace)
    return rc


def _add_common(p: argparse.ArgumentParser, workspace_required: bool = True) -> None:
    p.add_argument("--workspace", required=workspace_required, help="memoir workspace directory")
    p.add_argument("--adapter", choices=sorted(ADAPTERS), help="runtime adapter (default: auto)")


def _add_schedule_opts(p: argparse.ArgumentParser) -> None:
    p.add_argument("--daily-time", default="20:00", help="daily nudge HH:MM (default 20:00)")
    p.add_argument("--weekly-day", default="sun", help="weekly review day (default sun)")
    p.add_argument("--weekly-time", default="19:00", help="weekly review HH:MM (default 19:00)")
    p.add_argument("--notify", default="file", choices=notify_mod.PROVIDERS,
                   help="notification provider (default: file)")
    p.add_argument("--ntfy-topic", default="", help="ntfy.sh topic")
    p.add_argument("--telegram-token", default="", help="Telegram bot token")
    p.add_argument("--telegram-chat", default="", help="Telegram chat id")
    p.add_argument("--slack-webhook", default="", help="Slack incoming-webhook URL")
    p.add_argument("--channel", default="", help="openclaw: delivery channel")
    p.add_argument("--to", default="", help="openclaw: delivery target id")
    p.add_argument("--agent-cmd", default="",
                   help="generic: shell template with {prompt} placeholder")
    p.add_argument("--quiet-from", default="", help="no nudges from HH:MM (e.g. 22:00)")
    p.add_argument("--quiet-to", default="", help="no nudges until HH:MM (e.g. 08:00)")
    p.add_argument("--transcribe-cmd", default="",
                   help="voice capture: command printing a transcript, with {file} "
                        "(e.g. 'whisper-cli -f {file} --no-timestamps')")
    p.add_argument("--apply", action="store_true",
                   help="activate the schedule now (claude-code: merge crontab)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="memoir", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--version", action="version", version=f"memoir {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("detect", help="probe the host (read-only)")
    p.add_argument("--json", action="store_true")
    p.add_argument("--workspace", default="", help="optionally check a workspace too")
    p.set_defaults(func=cmd_detect)

    p = sub.add_parser("init", help="scaffold the workspace (C1)")
    _add_common(p)
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("install", help="install skills into the runtime (C2)")
    _add_common(p)
    p.add_argument("--agent-cmd", default="", help="generic: shell template with {prompt}")
    p.set_defaults(func=cmd_install)

    p = sub.add_parser("schedule", help="generate proactive jobs (C3) + notifier (C4)")
    _add_common(p)
    _add_schedule_opts(p)
    p.set_defaults(func=cmd_schedule)

    p = sub.add_parser("doctor", help="verify the installation end to end")
    _add_common(p)
    p.add_argument("--agent-cmd", default="")
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser(
        "run", help="stateful driver: execute one job or a writer reply"
    )
    p.add_argument("--workspace", required=True)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--job", choices=["daily-nudge", "weekly-review"])
    g.add_argument("--reply", default="", help="the writer's reply text")
    p.add_argument("--attempts", type=int, default=driver_mod.DEFAULT_ATTEMPTS)
    p.add_argument("--retry-delay", type=float, default=driver_mod.DEFAULT_RETRY_DELAY,
                   help="seconds; doubles per attempt")
    p.add_argument("--timeout", type=float, default=driver_mod.DEFAULT_TIMEOUT)
    p.add_argument("--force", action="store_true", help="ignore the quiet window")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("status", help="progress + loop-state dashboard")
    p.add_argument("--workspace", required=True)
    p.add_argument("--tail", type=int, default=5, help="show last N runs")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser(
        "capture", help="voice note / photo / typed note -> raw material in memories/"
    )
    p.add_argument("--workspace", required=True)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--file", default="", help="path to a voice note or photograph")
    g.add_argument("--text", default="", help="a quick typed note")
    p.add_argument("--kind", choices=["auto", "audio", "photo"], default="auto",
                   help="how to treat --file (default: from its extension)")
    p.add_argument("--note", default="", help="photo: what the writer said about it")
    p.add_argument("--no-agent", action="store_true",
                   help="just file it; don't ask the agent to shape it now")
    p.add_argument("--timeout", type=float, default=driver_mod.DEFAULT_TIMEOUT)
    p.add_argument("--transcribe-timeout", type=float,
                   default=capture_mod.DEFAULT_TRANSCRIBE_TIMEOUT)
    p.set_defaults(func=cmd_capture)

    p = sub.add_parser(
        "lint", help="truth-contract check: concrete details in chapters/ with no "
                     "trace in memories/"
    )
    p.add_argument("--workspace", required=True)
    p.add_argument("--chapters", default="", help="override the chapters directory")
    p.add_argument("--memories", default="", help="override the memories directory")
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.add_argument("--fail-on", choices=["never", "unsupported", "any"],
                   default="never",
                   help="exit non-zero on findings (default: never — it is advisory)")
    p.set_defaults(func=cmd_lint)

    p = sub.add_parser("care", help="pause/resume, quiet dates, cadence (the scheduler obeys)")
    care_sub = p.add_subparsers(dest="care_action", required=True)
    c = care_sub.add_parser("show", help="current care settings")
    c.add_argument("--workspace", required=True)
    c = care_sub.add_parser("pause", help="stop nudges for a while")
    c.add_argument("--workspace", required=True)
    c.add_argument("--days", type=int, default=care_mod.DEFAULT_PAUSE_DAYS)
    c.add_argument("--until", default="", help="ISO date (overrides --days)")
    c = care_sub.add_parser("resume", help="resume nudges")
    c.add_argument("--workspace", required=True)
    c = care_sub.add_parser("quiet", help="add quiet dates (e.g. an anniversary)")
    c.add_argument("--workspace", required=True)
    c.add_argument("--from", dest="date_from", required=True, help="ISO date")
    c.add_argument("--to", dest="date_to", default="", help="ISO date (default: same day)")
    c.add_argument("--reason", default="")
    c = care_sub.add_parser("cadence", help="base nudges per week (1-7)")
    c.add_argument("--workspace", required=True)
    c.add_argument("--per-week", type=int, required=True)
    for c in care_sub.choices.values():
        c.set_defaults(func=cmd_care)

    p = sub.add_parser("setup", help="init + install + schedule in one command")
    _add_common(p)
    _add_schedule_opts(p)
    p.set_defaults(func=cmd_setup)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
