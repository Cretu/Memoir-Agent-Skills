# Security & Privacy

This project's "assets" are unusually personal: memoirs contain sensitive detail about
the writer and their family. Treat privacy issues with the same severity as code
vulnerabilities.

## Data-handling model

- **All memoir content stays in the writer's workspace** (`memories/`, `chapters/`,
  `project_state.md`) on the machine running the agent. The skills never require
  sending manuscript content to third-party services beyond the model API itself.
- **Captured voice and photos stay local.** `memoir capture` writes transcripts to
  `memories/inbox/` and copies photographs into `memories/photos/` inside the
  workspace. Transcription runs through a command *you* configure
  (`--transcribe-cmd`) — no ASR service is bundled or contacted by default, so
  audio leaves the machine only if you point it at a remote one. The capture
  prompt instructs the agent to reply to the channel with a short
  acknowledgement only, never the memory content.
- **Chat channels are for nudges, not manuscripts.** Scheduled notifications
  (deployment layer, capability C4) route through third-party messaging providers.
  Adapters instruct keeping sensitive passages in local files and using the channel
  for short prompts and task reminders only.
- **Autonomous runs are constrained by design**: they may recall, organize, remind,
  and propose — never finalize prose or alter `chapters/` without the writer
  (see `memoir-orchestrator/SKILL.md` §5 and `memoir-ethics-and-care.md`).
- **Secrets** (bot tokens, webhook URLs) belong in the host's secret storage or
  environment configuration — never committed to the workspace or this repo.

## Reporting

If you find a way the skills or deployment guidance could leak memoir content,
weaken the consent/safety gates, or execute untrusted instructions:

1. **Do not open a public issue with exploit details.**
2. Use GitHub's private vulnerability reporting on this repository (Security →
   "Report a vulnerability"), or contact the maintainer directly.
3. Expect an acknowledgement within a week.

Hardening contributions (secret handling, tool-permission enforcement, PII-aware
channel guidance) are tracked in `ROADMAP.md` and very welcome.
