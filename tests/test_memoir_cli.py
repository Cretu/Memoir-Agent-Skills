"""Unit tests for the memoir CLI (stdlib unittest; no network, no side effects
outside temp dirs)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

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
