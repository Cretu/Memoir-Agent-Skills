"""Voice-first and photo-anchored capture (ROADMAP Phase 4).

For memoir work — especially with older writers — speaking beats typing, and a
photograph unlocks more than a blank prompt does. This module turns a voice
note, a photo, or a quick typed line into raw material in `memories/inbox/`,
then (optionally) lets the agent shape it into a proper Memory Capture.

Two deliberate design choices:

* **Transcription is pluggable, not bundled.** You supply the command
  (`--transcribe-cmd 'whisper-cli -f {file} --no-timestamps'`), the same way
  the generic adapter takes an agent command. No service is hardcoded, nothing
  is uploaded that you did not configure.
* **Memoir content never goes out through the notification channel.** The
  transcript is written to the local workspace; only the agent's short
  acknowledgement is delivered (see SECURITY.md). The capture prompt says so
  explicitly.
"""

from __future__ import annotations

import datetime as dt
import re
import shlex
import shutil
import subprocess
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from . import driver as driver_mod
from .contract import NO_PROSE_CLAUSE

FILE_PLACEHOLDER = "{file}"
DEFAULT_TRANSCRIBE_TIMEOUT = 900  # transcription of a long note is slow

INBOX = "memories/inbox"
PHOTOS = "memories/photos"

AUDIO_SUFFIXES = {".m4a", ".mp3", ".wav", ".ogg", ".oga", ".opus", ".aac", ".flac", ".mp4"}
PHOTO_SUFFIXES = {".jpg", ".jpeg", ".png", ".heic", ".webp", ".gif", ".tif", ".tiff"}

# The agent's stdout is delivered to a chat channel, so the prompt has to be
# explicit that the channel is not the place for the memoir itself.
CAPTURE_PROMPT = (
    "The writer just captured new raw material for their memoir: {rel}. "
    "As memoir-orchestrator: read it, shape it into a proper Memory Capture "
    "under memories/ following the data model (record ONLY what the writer "
    "actually said — never invent names, dates, or detail), note any thread "
    "worth following up, and update project_state.md.\n\n"
    "IMPORTANT: your printed output is sent to a chat channel. Keep it to a "
    "brief, warm acknowledgement plus ONE gentle follow-up question. Do not "
    "quote the memory content back — it stays in the workspace."
    + NO_PROSE_CLAUSE
)


@dataclass
class CaptureResult:
    path: Path                 # the inbox file that was written
    text: str                  # transcript / note text
    asset: Path | None = None  # copied photo, if any
    agent_ran: bool = False
    agent_output: str = ""
    delivered: bool = False


# -- helpers ------------------------------------------------------------------

def slugify(text: str, max_len: int = 48) -> str:
    """Filename-safe slug that keeps non-Latin scripts readable."""
    text = unicodedata.normalize("NFKC", text).strip()
    text = re.sub(r"[\s/\\]+", "-", text)
    text = re.sub(r"[^\w\-]", "", text, flags=re.UNICODE)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text[:max_len] or "capture"


def _stamp(now: dt.datetime | None = None) -> str:
    return (now or dt.datetime.now()).strftime("%Y-%m-%d-%H%M")


def transcribe(
    workspace: Path, audio: Path, timeout: float = DEFAULT_TRANSCRIBE_TIMEOUT
) -> str:
    """Run the configured transcription command; return its stdout."""
    cfg = driver_mod.load_config(workspace)
    template = cfg.get("transcribe_cmd", "")
    if not template:
        raise SystemExit(
            "no transcription command configured. Set one with:\n"
            "  memoir schedule --workspace <ws> --transcribe-cmd "
            "'whisper-cli -f {file} --no-timestamps'\n"
            "(any command that prints the transcript to stdout works)"
        )
    if FILE_PLACEHOLDER not in template:
        raise SystemExit("--transcribe-cmd must contain the {file} placeholder")
    if not audio.is_file():
        raise SystemExit(f"audio file not found: {audio}")

    command = template.replace(FILE_PLACEHOLDER, shlex.quote(str(audio.resolve())))
    try:
        proc = subprocess.run(
            command, shell=True, text=True, capture_output=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        raise SystemExit(f"transcription timed out after {timeout}s") from None
    if proc.returncode != 0:
        raise SystemExit(
            f"transcription failed (exit {proc.returncode}): {proc.stderr.strip()[:400]}"
        )
    text = proc.stdout.strip()
    if not text:
        raise SystemExit("transcription produced no text — nothing captured")
    return text


# -- writing captures ---------------------------------------------------------

def _write_inbox(
    workspace: Path,
    kind: str,
    text: str,
    source: str,
    asset_rel: str = "",
    now: dt.datetime | None = None,
) -> Path:
    inbox = workspace / INBOX
    inbox.mkdir(parents=True, exist_ok=True)
    first_line = next((ln for ln in text.splitlines() if ln.strip()), kind)
    name = f"{_stamp(now)}-{slugify(first_line)}.md"
    path = inbox / name

    header = [
        f"# Raw capture — {kind}",
        "",
        f"- Captured: {(now or dt.datetime.now()).isoformat(timespec='minutes')}",
        f"- Source: {source}",
        "- Status: **raw** — not yet shaped into a Memory Capture",
    ]
    if asset_rel:
        header.append(f"- Photo: [{asset_rel}](../../{asset_rel})")
    header += ["", "---", "", text, ""]
    path.write_text("\n".join(header), encoding="utf-8")
    return path


def _run_agent(workspace: Path, rel: str, timeout: float) -> tuple[bool, str, bool]:
    """Ask the agent to shape the capture. Returns (ran, output, delivered)."""
    cfg = driver_mod.load_config(workspace)
    if not cfg.get("adapter"):
        return False, "", False
    adapter = driver_mod._adapter_for(workspace, cfg)
    command = adapter.agent_command(workspace, CAPTURE_PROMPT.format(rel=rel))
    result = driver_mod._execute(
        workspace, "capture", "shape", command,
        attempts=1, retry_delay=0, timeout=timeout,
    )
    return True, result.output, result.delivered


def capture_text(
    workspace: Path, text: str, source: str = "typed note",
    run_agent: bool = True, timeout: float = driver_mod.DEFAULT_TIMEOUT,
) -> CaptureResult:
    text = text.strip()
    if not text:
        raise SystemExit("nothing to capture (empty text)")
    path = _write_inbox(workspace, "typed note", text, source)
    result = CaptureResult(path, text)
    if run_agent:
        result.agent_ran, result.agent_output, result.delivered = _run_agent(
            workspace, path.relative_to(workspace).as_posix(), timeout
        )
    return result


def capture_voice(
    workspace: Path, audio: Path, run_agent: bool = True,
    transcribe_timeout: float = DEFAULT_TRANSCRIBE_TIMEOUT,
    timeout: float = driver_mod.DEFAULT_TIMEOUT,
) -> CaptureResult:
    text = transcribe(workspace, audio, transcribe_timeout)
    path = _write_inbox(workspace, "voice note", text, f"voice note ({audio.name})")
    result = CaptureResult(path, text)
    if run_agent:
        result.agent_ran, result.agent_output, result.delivered = _run_agent(
            workspace, path.relative_to(workspace).as_posix(), timeout
        )
    return result


def capture_photo(
    workspace: Path, image: Path, note: str = "", run_agent: bool = True,
    timeout: float = driver_mod.DEFAULT_TIMEOUT,
) -> CaptureResult:
    """Copy the photo into the workspace and open a capture anchored to it.

    The photo stays local; runtimes whose agent can read image files will look
    at it directly when shaping the capture.
    """
    if not image.is_file():
        raise SystemExit(f"image file not found: {image}")
    photos = workspace / PHOTOS
    photos.mkdir(parents=True, exist_ok=True)
    dest = photos / f"{_stamp()}-{slugify(note or image.stem)}{image.suffix.lower()}"
    shutil.copy2(image, dest)

    body = note.strip() or (
        "(no note yet — the writer will say what this picture is about)"
    )
    asset_rel = dest.relative_to(workspace).as_posix()
    path = _write_inbox(
        workspace, "photo", body, f"photograph ({image.name})", asset_rel=asset_rel
    )
    result = CaptureResult(path, body, asset=dest)
    if run_agent:
        result.agent_ran, result.agent_output, result.delivered = _run_agent(
            workspace, path.relative_to(workspace).as_posix(), timeout
        )
    return result


def guess_kind(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in AUDIO_SUFFIXES:
        return "audio"
    if suffix in PHOTO_SUFFIXES:
        return "photo"
    return "unknown"


def inbox_status(workspace: Path) -> tuple[int, list[str]]:
    """(count, newest-first names) of raw captures awaiting shaping."""
    inbox = workspace / INBOX
    if not inbox.is_dir():
        return 0, []
    files = sorted(inbox.glob("*.md"), key=lambda p: p.name, reverse=True)
    return len(files), [p.name for p in files]
