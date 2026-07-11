"""Unit tests for the memoir CLI (stdlib unittest; no network, no side effects
outside temp dirs)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from memoir_cli import adaptive as adaptive_mod
from memoir_cli import care as care_mod
from memoir_cli import detect as detect_mod
from memoir_cli import driver as driver_mod
from memoir_cli import notify as notify_mod
from memoir_cli import workspace as ws_mod
from memoir_cli.adapters.claude_code import (
    ClaudeCodeAdapter,
    map_allowed_tools,
)
from memoir_cli.adapters.generic import GenericCronAdapter
from memoir_cli.adapters.openclaw import OpenClawAdapter
from memoir_cli.contract import SKILL_DIRS
from memoir_cli.jobs import standard_jobs

REPO = Path(__file__).resolve().parents[1]


class TestToolMapping(unittest.TestCase):
    def test_maps_abstract_tools_to_claude_code(self):
        src = (
            "---\nname: x\ndescription: d\nallowed-tools:\n"
            "  - text-generation\n  - memory\n  - read_file\n"
            "  - write_file\n  - list_directory\n---\n# body\n"
        )
        out = map_allowed_tools(src)
        self.assertIn("allowed-tools:\n  - Read\n  - Write\n  - Edit\n  - Glob\n", out)
        self.assertNotIn("read_file", out)
        self.assertNotIn("text-generation", out)
        self.assertIn("# body", out)

    def test_no_allowed_tools_block_is_untouched(self):
        src = "---\nname: x\ndescription: d\n---\nbody\n"
        self.assertEqual(map_allowed_tools(src), src)


class TestWorkspace(unittest.TestCase):
    def test_init_is_idempotent_and_preserves_edits(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "ws"
            created = ws_mod.init(REPO, ws)
            self.assertIn("memories/", created)
            self.assertTrue((ws / "project_state.md").is_file())
            # simulate the writer editing their ledger
            (ws / "project_state.md").write_text("MY EDITS", encoding="utf-8")
            created2 = ws_mod.init(REPO, ws)
            self.assertEqual(created2, [])
            self.assertEqual((ws / "project_state.md").read_text(), "MY EDITS")

    def test_doctor_flags_missing_workspace(self):
        checks = ws_mod.doctor(Path("/nonexistent/nowhere"))
        self.assertFalse(checks[0].ok)


class TestClaudeCodeAdapter(unittest.TestCase):
    def _installed(self, tmp: str) -> Path:
        ws = Path(tmp) / "ws"
        ws_mod.init(REPO, ws)
        adapter = ClaudeCodeAdapter()
        names = adapter.install_skills(REPO, ws)
        self.assertEqual(sorted(names), sorted(SKILL_DIRS))
        return ws

    def test_install_rewrites_tools_and_copies_support_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._installed(tmp)
            skill = ws / ".claude" / "skills" / "memoir-orchestrator"
            text = (skill / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("- Read", text)
            self.assertNotIn("- read_file", text)
            self.assertTrue((skill / "references" / "reference.md").is_file())

    def test_schedule_enforces_chapter_deny_and_writes_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._installed(tmp)
            adapter = ClaudeCodeAdapter()
            script = notify_mod.write_notifier(ws, "file", {})
            artifacts, instructions = adapter.schedule(
                ws, standard_jobs("21:30", "wed", "18:00"), str(script)
            )
            settings = json.loads((ws / ".memoir" / "autonomous-settings.json").read_text())
            self.assertIn("Write(./chapters/**)", settings["permissions"]["deny"])
            # cron lines go through the stateful driver, not a bare agent call
            cron = (ws / ".memoir" / "cron.txt").read_text()
            self.assertIn("30 21 * * *", cron)          # daily at 21:30
            self.assertIn("0 18 * * 3", cron)           # weekly on wednesday
            self.assertIn("run --workspace", cron)
            self.assertIn("--job daily-nudge", cron)
            # the underlying agent command keeps the guardrails + truth contract
            agent_cmd = adapter.agent_command(ws, standard_jobs()[0].prompt)
            self.assertIn("--settings", agent_cmd)
            self.assertIn("Do NOT draft", agent_cmd)
            timer = (ws / ".memoir" / "systemd" / "memoir-weekly-review.timer").read_text()
            self.assertIn("OnCalendar=Wed *-*-* 18:00:00", timer)
            self.assertIn("systemctl --user", instructions)
            self.assertTrue(all(a.exists() for a in artifacts))

    def test_reply_command_continues_session_with_guardrails(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            adapter = ClaudeCodeAdapter()
            cmd = adapter.reply_command(ws, "the writer said something")
            self.assertIn("--continue", cmd)
            self.assertIn("--settings", cmd)

    def test_doctor_passes_after_full_setup(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._installed(tmp)
            adapter = ClaudeCodeAdapter()
            script = notify_mod.write_notifier(ws, "file", {})
            adapter.schedule(ws, standard_jobs(), str(script))
            failures = [
                c for c in ws_mod.doctor(ws) + adapter.doctor(REPO, ws)
                if not c.ok
                # environment-dependent checks may fail in CI (no claude binary,
                # no crontab); everything the CLI itself controls must pass
                and c.name not in ("claude CLI on PATH", "crontab contains managed block")
            ]
            self.assertEqual(failures, [], f"unexpected failures: {failures}")


class TestNotify(unittest.TestCase):
    def test_secret_providers_write_protected_env(self):
        secret = "sekret-token-12345"
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            notify_mod.write_notifier(
                ws, "telegram", {"telegram_token": secret, "telegram_chat": "42"}
            )
            env = ws / ".memoir" / "notify.env"
            self.assertTrue(env.is_file())
            self.assertEqual(env.stat().st_mode & 0o777, 0o600)
            self.assertIn(secret, env.read_text())
            # the secret must live only in the 0600 env file, never in the script
            script = (ws / ".memoir" / "notify.sh").read_text()
            self.assertNotIn(secret, script)

    def test_missing_secret_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                notify_mod.write_notifier(Path(tmp), "ntfy", {"ntfy_topic": ""})


class TestOtherAdapters(unittest.TestCase):
    def test_openclaw_emits_cron_commands(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            adapter = OpenClawAdapter(channel="telegram", to="12345")
            artifacts, _ = adapter.schedule(ws, standard_jobs(), "")
            text = artifacts[0].read_text()
            self.assertIn("openclaw cron create", text)
            self.assertIn("--channel telegram --to 12345", text)
            self.assertIn("--session isolated", text)

    def test_generic_requires_prompt_placeholder(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            adapter = GenericCronAdapter(agent_cmd="my-agent --once")
            with self.assertRaises(SystemExit):
                adapter.agent_command(ws, "hello")
            adapter.agent_cmd = "my-agent --once {prompt}"
            cmd = adapter.agent_command(ws, "hello world")
            self.assertIn("my-agent --once 'hello world'", cmd)


class TestDriver(unittest.TestCase):
    """Stateful driver (memoir run): retries, quiet hours, reply, logging."""

    def _ws_with_stub(self, tmp: str, fail_times: int) -> Path:
        """Workspace on the generic adapter whose 'agent' is a stub that fails
        `fail_times` times, then prints a message."""
        ws = Path(tmp) / "ws"
        ws_mod.init(REPO, ws)
        notify_mod.write_notifier(ws, "file", {})
        stub = Path(tmp) / "stub.sh"
        counter = Path(tmp) / "count"
        stub.write_text(
            "#!/bin/sh\n"
            f'n=$(cat "{counter}" 2>/dev/null || echo 0)\n'
            f'echo $((n+1)) > "{counter}"\n'
            f"[ $((n)) -lt {fail_times} ] && exit 1\n"
            'echo "nudge for: $1"\n',
            encoding="utf-8",
        )
        stub.chmod(0o755)
        driver_mod.save_config(
            ws, {"adapter": "generic", "agent_cmd": f"{stub} {{prompt}}"}
        )
        return ws

    def test_retries_then_succeeds_and_delivers(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._ws_with_stub(tmp, fail_times=2)
            result = driver_mod.run_job(ws, "daily-nudge", retry_delay=0)
            self.assertTrue(result.ok)
            self.assertEqual(result.attempts, 3)
            self.assertTrue(result.delivered)
            # delivered through the file notifier
            self.assertIn("nudge for:", (ws / ".memoir" / "nudges.log").read_text())
            # structured log + durable state
            runs = [
                json.loads(line)
                for line in (ws / ".memoir" / "runs.jsonl").read_text().splitlines()
            ]
            self.assertEqual(len(runs), 1)
            self.assertTrue(runs[0]["ok"])
            self.assertEqual(runs[0]["attempts"], 3)
            state = driver_mod.load_state(ws)
            self.assertEqual(state["jobs"]["daily-nudge"]["consecutive_failures"], 0)

    def test_exhausted_retries_recorded_as_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._ws_with_stub(tmp, fail_times=99)
            result = driver_mod.run_job(ws, "daily-nudge", attempts=2, retry_delay=0)
            self.assertFalse(result.ok)
            state = driver_mod.load_state(ws)
            self.assertEqual(state["jobs"]["daily-nudge"]["consecutive_failures"], 1)

    def test_quiet_window_skips_but_force_overrides(self):
        import datetime as dt
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._ws_with_stub(tmp, fail_times=0)
            cfg = driver_mod.load_config(ws)
            cfg.update({"quiet_from": "22:00", "quiet_to": "08:00"})
            driver_mod.save_config(ws, cfg)
            inside = dt.time(23, 30)
            result = driver_mod.run_job(ws, "daily-nudge", now=inside, retry_delay=0)
            self.assertTrue(result.ok)
            self.assertEqual(result.attempts, 0)      # nothing executed
            self.assertIn("quiet", result.error)
            forced = driver_mod.run_job(
                ws, "daily-nudge", now=inside, force=True, retry_delay=0
            )
            self.assertEqual(forced.attempts, 1)

    def test_quiet_window_midnight_wrap(self):
        import datetime as dt
        self.assertTrue(driver_mod.in_quiet_window(dt.time(23, 0), "22:00", "08:00"))
        self.assertTrue(driver_mod.in_quiet_window(dt.time(7, 59), "22:00", "08:00"))
        self.assertFalse(driver_mod.in_quiet_window(dt.time(12, 0), "22:00", "08:00"))
        self.assertFalse(driver_mod.in_quiet_window(dt.time(12, 0), "", ""))

    def test_reply_flows_through_and_updates_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._ws_with_stub(tmp, fail_times=0)
            result = driver_mod.run_reply(ws, "I remember the red bicycle", retry_delay=0)
            self.assertTrue(result.ok)
            self.assertIn("red bicycle", result.output)
            self.assertIsNotNone(driver_mod.load_state(ws)["last_reply_at"])

    def test_status_renders_dashboard(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._ws_with_stub(tmp, fail_times=0)
            (ws / "memories" / "the-red-bicycle.md").write_text("m", encoding="utf-8")
            driver_mod.run_job(ws, "daily-nudge", retry_delay=0)
            out = driver_mod.status(ws)
            self.assertIn("memories:  1", out)
            self.assertIn("job daily-nudge", out)
            self.assertIn("[ok]", out)


class TestAdaptive(unittest.TestCase):
    """Caring adaptive engine: backoff on silence, reset on reply, hard stops."""

    NOW = None  # set per test via _now

    def _now(self):
        import datetime as dt
        return dt.datetime.now(dt.timezone.utc)

    def _seed_nudges(self, ws: Path, ago_days: list[float]) -> None:
        """Seed runs.jsonl with delivered daily nudges N days in the past."""
        import datetime as dt
        lines = []
        for ago in sorted(ago_days, reverse=True):
            ts = (self._now() - dt.timedelta(days=ago)).isoformat(timespec="seconds")
            lines.append(json.dumps({
                "ts": ts, "kind": "job", "id": "daily-nudge",
                "ok": True, "delivered": True,
            }))
        (ws / ".memoir").mkdir(parents=True, exist_ok=True)
        (ws / ".memoir" / "runs.jsonl").write_text("\n".join(lines) + "\n")

    def _set_last_reply(self, ws: Path, ago_days: float) -> None:
        import datetime as dt
        state = driver_mod.load_state(ws)
        state["last_reply_at"] = (
            self._now() - dt.timedelta(days=ago_days)
        ).isoformat(timespec="seconds")
        driver_mod.save_state(ws, state)

    def test_fresh_workspace_sends_normally(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = adaptive_mod.decide(Path(tmp))
            self.assertTrue(d.send)
            self.assertFalse(d.soften)

    def test_reply_resets_the_ladder(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            self._seed_nudges(ws, [5, 4, 3, 2])
            self._set_last_reply(ws, 1.5)  # replied after all of them
            d = adaptive_mod.decide(ws)
            self.assertEqual(d.silent_streak, 0)
            self.assertTrue(d.send)
            self.assertFalse(d.soften)

    def test_three_unanswered_backs_off_and_softens(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            self._seed_nudges(ws, [3, 2, 1])       # 3 unanswered, last 1d ago
            d = adaptive_mod.decide(ws)
            self.assertFalse(d.send)                # 2-day gap not yet elapsed
            self.assertEqual(d.silent_streak, 3)
            self._seed_nudges(ws, [4, 3, 2.5])      # last one 2.5d ago
            d = adaptive_mod.decide(ws)
            self.assertTrue(d.send)
            self.assertTrue(d.soften)               # sends, but gently

    def test_six_unanswered_reaches_weekly_floor(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            self._seed_nudges(ws, [20, 18, 16, 14, 12, 10, 3])
            d = adaptive_mod.decide(ws)
            self.assertFalse(d.send)                # 7d gap, only 3d elapsed
            self._seed_nudges(ws, [24, 22, 20, 18, 16, 14, 8])
            d = adaptive_mod.decide(ws)
            self.assertTrue(d.send)
            self.assertTrue(d.soften)

    def test_pause_and_quiet_dates_are_hard_stops(self):
        import datetime as dt
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            care_mod.set_pause(ws, dt.date.today() + dt.timedelta(days=5))
            d = adaptive_mod.decide(ws)
            self.assertFalse(d.send)
            self.assertIn("paused", d.reason)
            care_mod.clear_pause(ws)
            today = dt.date.today().isoformat()
            care_mod.add_quiet_dates(ws, today, today, "anniversary")
            d = adaptive_mod.decide(ws)
            self.assertFalse(d.send)
            self.assertIn("anniversary", d.reason)

    def test_expired_pause_no_longer_blocks(self):
        import datetime as dt
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            care_mod.set_pause(ws, dt.date.today() - dt.timedelta(days=1))
            self.assertTrue(adaptive_mod.decide(ws).send)

    def test_writer_cadence_widens_base_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            care_mod.set_cadence(ws, 2)             # ~every 3.5 days
            self._seed_nudges(ws, [1])
            self._set_last_reply(ws, 0.5)           # engaged writer
            d = adaptive_mod.decide(ws)
            self.assertFalse(d.send)                # own cadence says wait
            self.assertFalse(d.soften)

    def test_care_mutations_never_leak_between_workspaces(self):
        """Regression: care.load() must deep-copy defaults — a quiet window
        added in one workspace must not appear in another."""
        import datetime as dt
        today = dt.date.today().isoformat()
        with tempfile.TemporaryDirectory() as tmp_a, \
                tempfile.TemporaryDirectory() as tmp_b:
            care_mod.add_quiet_dates(Path(tmp_a), today, today, "private")
            care_mod.set_cadence(Path(tmp_a), 2)
            other = care_mod.load(Path(tmp_b))
            self.assertEqual(other["quiet_dates"], [])
            self.assertEqual(other["cadence"]["nudges_per_week"], 7)

    def test_corrupt_care_file_fails_safe(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            care_path = care_mod.care_path(ws)
            care_path.write_text("{not json", encoding="utf-8")
            self.assertTrue(adaptive_mod.decide(ws).send)  # defaults, no crash


class TestDriverCareIntegration(unittest.TestCase):
    def _ws(self, tmp: str) -> Path:
        ws = Path(tmp) / "ws"
        ws_mod.init(REPO, ws)
        notify_mod.write_notifier(ws, "file", {})
        stub = Path(tmp) / "stub.sh"
        stub.write_text('#!/bin/sh\necho "agent got: $1"\n', encoding="utf-8")
        stub.chmod(0o755)
        driver_mod.save_config(
            ws, {"adapter": "generic", "agent_cmd": f"{stub} {{prompt}}"}
        )
        return ws

    def test_paused_workspace_skips_both_jobs(self):
        import datetime as dt
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._ws(tmp)
            care_mod.set_pause(ws, dt.date.today() + dt.timedelta(days=3))
            for job in ("daily-nudge", "weekly-review"):
                result = driver_mod.run_job(ws, job, retry_delay=0)
                self.assertTrue(result.ok)
                self.assertEqual(result.attempts, 0, job)
                self.assertIn("paused", result.error)

    def test_softened_nudge_carries_the_modifier(self):
        import datetime as dt
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._ws(tmp)
            lines = []
            for ago in (5, 4, 3):
                ts = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=ago))
                lines.append(json.dumps({
                    "ts": ts.isoformat(timespec="seconds"), "kind": "job",
                    "id": "daily-nudge", "ok": True, "delivered": True,
                }))
            (ws / ".memoir" / "runs.jsonl").write_text("\n".join(lines) + "\n")
            result = driver_mod.run_job(ws, "daily-nudge", retry_delay=0)
            self.assertTrue(result.ok)
            self.assertIn("one sentence is enough", result.output)

    def test_pause_keyword_reply_pauses_without_agent(self):
        import datetime as dt
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._ws(tmp)
            result = driver_mod.run_reply(ws, "暂停", retry_delay=0)
            self.assertTrue(result.ok)
            self.assertNotIn("agent got:", result.output)   # agent never called
            self.assertIn("已暂停", result.output)
            self.assertTrue(care_mod.is_paused(care_mod.load(ws), dt.date.today()))
            # confirmation went out through the notifier
            self.assertIn("已暂停", (ws / ".memoir" / "nudges.log").read_text())
            # and '继续' while paused resumes (only acts when paused)
            result = driver_mod.run_reply(ws, "继续", retry_delay=0)
            self.assertFalse(care_mod.is_paused(care_mod.load(ws), dt.date.today()))
            self.assertIn("欢迎回来", result.output)

    def test_resume_word_flows_to_agent_when_not_paused(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._ws(tmp)
            result = driver_mod.run_reply(ws, "继续", retry_delay=0)
            self.assertIn("agent got:", result.output)      # normal reply path


class TestDetect(unittest.TestCase):
    def test_probe_shape(self):
        report = detect_mod.probe()
        self.assertIn("recommended_adapter", report)
        self.assertIn("claude-code", report["runtimes"])
        self.assertIsInstance(report["semi_auto_only"], bool)
        # renders without crashing
        self.assertIn("Recommended adapter:", detect_mod.render(report))


if __name__ == "__main__":
    unittest.main()
