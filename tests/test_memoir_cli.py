"""Unit tests for the memoir CLI (stdlib unittest; no network, no side effects
outside temp dirs)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from memoir_cli import detect as detect_mod
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
            cron = (ws / ".memoir" / "cron.txt").read_text()
            self.assertIn("30 21 * * *", cron)          # daily at 21:30
            self.assertIn("0 18 * * 3", cron)           # weekly on wednesday
            self.assertIn("--settings", cron)
            self.assertIn("Do NOT draft", cron)
            timer = (ws / ".memoir" / "systemd" / "memoir-weekly-review.timer").read_text()
            self.assertIn("OnCalendar=Wed *-*-* 18:00:00", timer)
            self.assertIn("systemctl --user", instructions)
            self.assertTrue(all(a.exists() for a in artifacts))

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
