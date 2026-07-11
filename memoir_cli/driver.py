"""The stateful driver (ROADMAP Phase 2).

`memoir run` is the single entrypoint the scheduler invokes — instead of a bare
one-shot agent call in a cron line, every unattended turn now gets:

  * retries with exponential backoff,
  * a quiet-hours guard (config; --force overrides),
  * delivery through the configured notifier (C4),
  * a structured JSONL run log (.memoir/runs.jsonl),
  * durable loop state with atomic writes (.memoir/driver-state.json),
  * a reply path (`memoir run --reply "..."`) so the writer's answer feeds the
    next agent turn — with session continuity where the runtime supports it.

The driver owns *loop mechanics* only. The memoir's own state stays in
`project_state.md`, owned by the skills — that separation is what keeps the
skills portable (see deployment/capability-contract.md, portable invariants).
"""

from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from .adapters import get_adapter
from .adapters.generic import GenericCronAdapter
from .contract import memoir_dir
from .jobs import REPLY_PREAMBLE, standard_jobs

DEFAULT_ATTEMPTS = 3
DEFAULT_RETRY_DELAY = 30  # seconds; doubles per attempt
DEFAULT_TIMEOUT = 600     # seconds per agent turn


@dataclass
class RunResult:
    ok: bool
    delivered: bool
    attempts: int
    output: str
    error: str = ""


# -- config & state ----------------------------------------------------------

def config_path(workspace: Path) -> Path:
    return memoir_dir(workspace) / "config.json"


def load_config(workspace: Path) -> dict:
    p = config_path(workspace)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def save_config(workspace: Path, cfg: dict) -> None:
    _atomic_write(config_path(workspace), json.dumps(cfg, indent=2) + "\n")


def state_path(workspace: Path) -> Path:
    return memoir_dir(workspace) / "driver-state.json"


def load_state(workspace: Path) -> dict:
    p = state_path(workspace)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass  # corrupt state must never kill a run; start fresh
    return {"jobs": {}, "last_reply_at": None}


def save_state(workspace: Path, state: dict) -> None:
    _atomic_write(state_path(workspace), json.dumps(state, indent=2) + "\n")


def _atomic_write(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def log_run(workspace: Path, entry: dict) -> None:
    entry = {"ts": _now_iso(), **entry}
    with (memoir_dir(workspace) / "runs.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


# -- quiet hours --------------------------------------------------------------

def in_quiet_window(now: dt.time, quiet_from: str, quiet_to: str) -> bool:
    """True if `now` falls inside [quiet_from, quiet_to); supports midnight wrap."""
    if not quiet_from or not quiet_to:
        return False
    start = dt.time(*map(int, quiet_from.split(":")))
    end = dt.time(*map(int, quiet_to.split(":")))
    if start <= end:
        return start <= now < end
    return now >= start or now < end  # e.g. 22:00 -> 07:00


# -- execution ----------------------------------------------------------------

def _adapter_for(workspace: Path, cfg: dict):
    adapter = get_adapter(cfg.get("adapter", "claude-code"))
    if isinstance(adapter, GenericCronAdapter):
        adapter.agent_cmd = cfg.get("agent_cmd", "")
    return adapter


def _deliver(workspace: Path, text: str) -> bool:
    notify = memoir_dir(workspace) / "notify.sh"
    if not notify.exists() or not text.strip():
        return False
    proc = subprocess.run(
        [str(notify)], input=text, text=True, capture_output=True
    )
    return proc.returncode == 0


def _execute(
    workspace: Path,
    kind: str,
    run_id: str,
    command: str,
    attempts: int,
    retry_delay: float,
    timeout: float,
) -> RunResult:
    output, error = "", ""
    ok = False
    attempt = 0
    for attempt in range(1, attempts + 1):
        try:
            proc = subprocess.run(
                command, shell=True, text=True, capture_output=True, timeout=timeout
            )
            output, error = proc.stdout, proc.stderr[-2000:]
            ok = proc.returncode == 0
        except subprocess.TimeoutExpired:
            output, error, ok = "", f"timeout after {timeout}s", False
        if ok:
            break
        if attempt < attempts:
            time.sleep(retry_delay * (2 ** (attempt - 1)))

    delivered = _deliver(workspace, output) if ok else False

    state = load_state(workspace)
    job_state = state["jobs"].setdefault(run_id, {})
    job_state["last_run"] = _now_iso()
    if ok:
        job_state["last_success"] = _now_iso()
        job_state["consecutive_failures"] = 0
    else:
        job_state["consecutive_failures"] = job_state.get("consecutive_failures", 0) + 1
    if kind == "reply":
        state["last_reply_at"] = _now_iso()
    save_state(workspace, state)

    log_run(
        workspace,
        {
            "kind": kind,
            "id": run_id,
            "ok": ok,
            "attempts": attempt,
            "delivered": delivered,
            "output_bytes": len(output.encode()),
            **({"error": error} if error and not ok else {}),
        },
    )
    return RunResult(ok, delivered, attempt, output, error)


def run_job(
    workspace: Path,
    job_id: str,
    attempts: int = DEFAULT_ATTEMPTS,
    retry_delay: float = DEFAULT_RETRY_DELAY,
    timeout: float = DEFAULT_TIMEOUT,
    force: bool = False,
    now: dt.time | None = None,
) -> RunResult:
    cfg = load_config(workspace)
    now = now or dt.datetime.now().time()
    if not force and in_quiet_window(now, cfg.get("quiet_from", ""), cfg.get("quiet_to", "")):
        log_run(workspace, {"kind": "job", "id": job_id, "ok": True, "skipped": "quiet-window"})
        return RunResult(True, False, 0, "", "skipped: quiet window")

    jobs = {j.id: j for j in standard_jobs()}
    if job_id not in jobs:
        raise SystemExit(f"unknown job {job_id!r}; available: {', '.join(jobs)}")
    adapter = _adapter_for(workspace, cfg)
    command = adapter.agent_command(workspace, jobs[job_id].prompt)
    return _execute(workspace, "job", job_id, command, attempts, retry_delay, timeout)


def run_reply(
    workspace: Path,
    text: str,
    attempts: int = DEFAULT_ATTEMPTS,
    retry_delay: float = DEFAULT_RETRY_DELAY,
    timeout: float = DEFAULT_TIMEOUT,
) -> RunResult:
    """Feed the writer's reply into the loop. Never quiet-gated: the writer
    spoke first, so answering is not a nudge."""
    cfg = load_config(workspace)
    adapter = _adapter_for(workspace, cfg)
    prompt = REPLY_PREAMBLE + text
    command_fn = getattr(adapter, "reply_command", adapter.agent_command)
    command = command_fn(workspace, prompt)
    return _execute(workspace, "reply", "reply", command, attempts, retry_delay, timeout)


# -- status dashboard ---------------------------------------------------------

def status(workspace: Path, tail: int = 5) -> str:
    memories = [
        p for p in (workspace / "memories").glob("*.md") if p.name != "style_guide.md"
    ] if (workspace / "memories").is_dir() else []
    chapters = [
        p for p in (workspace / "chapters").glob("*.md")
        if p.name != "authors_note_flags.md"
    ] if (workspace / "chapters").is_dir() else []
    state = load_state(workspace)
    cfg = load_config(workspace)

    lines = [
        f"workspace: {workspace}",
        f"adapter:   {cfg.get('adapter', '(not configured)')}",
        f"memories:  {len(memories)}   chapters: {len(chapters)}",
        f"last reply from writer: {state.get('last_reply_at') or 'never'}",
    ]
    for job_id, js in sorted(state.get("jobs", {}).items()):
        fails = js.get("consecutive_failures", 0)
        lines.append(
            f"job {job_id}: last run {js.get('last_run', 'never')}, "
            f"last success {js.get('last_success', 'never')}"
            + (f", {fails} consecutive failure(s)" if fails else "")
        )
    runs_file = memoir_dir(workspace) / "runs.jsonl"
    if runs_file.exists() and tail > 0:
        lines.append(f"last {tail} runs:")
        for raw in runs_file.read_text(encoding="utf-8").splitlines()[-tail:]:
            try:
                e = json.loads(raw)
            except json.JSONDecodeError:
                continue
            mark = "ok" if e.get("ok") else "FAIL"
            extra = e.get("skipped") or e.get("error", "")
            lines.append(
                f"  [{mark}] {e.get('ts', '?')} {e.get('kind')}/{e.get('id')}"
                + (f" ({extra})" if extra else "")
            )
    return "\n".join(lines)
