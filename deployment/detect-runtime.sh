#!/bin/sh
# detect-runtime.sh — read-only probe for the memoir agent's host capabilities.
# It changes nothing; it inspects what's installed and prints which adapter to use.
# Capabilities (see capability-contract.md): C1 files, C2 skills, C3 schedule, C4 notify.

set -u
has() { command -v "$1" >/dev/null 2>&1; }
yes() { printf '  [x] %s\n' "$1"; }
no()  { printf '  [ ] %s\n' "$1"; }

echo "=================================================="
echo " Memoir agent — runtime & capability detection"
echo "=================================================="

# ---- Runtimes (C2 host) -------------------------------------------------------
echo
echo "Runtimes:"
RT=""
if has openclaw; then yes "OpenClaw CLI (openclaw)"; RT="openclaw"; else no "OpenClaw CLI"; fi
if has claude;   then yes "Claude Code CLI (claude)"; [ -z "$RT" ] && RT="claude-code"; else no "Claude Code CLI"; fi

SDK=""
if has python3 && python3 -c "import claude_agent_sdk" >/dev/null 2>&1; then
  yes "Claude Agent SDK (python: claude_agent_sdk)"; SDK="py"
elif has pip3 && pip3 show claude-agent-sdk >/dev/null 2>&1; then
  yes "Claude Agent SDK (pip: claude-agent-sdk)"; SDK="py"
elif [ -f package.json ] && grep -q "claude-agent-sdk" package.json 2>/dev/null; then
  yes "Claude Agent SDK (node: @anthropic-ai/claude-agent-sdk)"; SDK="js"
else
  no "Claude Agent SDK (python/node)"
fi
[ -z "$RT" ] && [ -n "$SDK" ] && RT="claude-agent-sdk"

# ---- C3: schedulers -----------------------------------------------------------
echo
echo "C3 — schedulers:"
SCHED=""
if has crontab;   then yes "cron (crontab)";        SCHED="cron"; else no "cron (crontab)"; fi
if has launchctl; then yes "launchd (macOS)";        [ -z "$SCHED" ] && SCHED="launchd"; else no "launchd (macOS)"; fi
if has systemctl; then yes "systemd timers";         [ -z "$SCHED" ] && SCHED="systemd"; else no "systemd timers"; fi
[ "$RT" = "openclaw" ] && { yes "OpenClaw native cron + heartbeat"; SCHED="openclaw-native"; }

# ---- C4: notification outlets -------------------------------------------------
echo
echo "C4 — notification outlets:"
NOTIFY=""
if has curl; then yes "curl  (ntfy / Telegram / Slack webhooks)"; NOTIFY="curl"; else no "curl (webhooks)"; fi
if has mail || has sendmail; then yes "mail / sendmail"; [ -z "$NOTIFY" ] && NOTIFY="mail"; else no "mail / sendmail"; fi
[ "$RT" = "openclaw" ] && { yes "OpenClaw native channels (WhatsApp/Telegram/…)"; NOTIFY="openclaw-native"; }

# ---- C1: workspace ------------------------------------------------------------
echo
echo "C1 — workspace (data model):"
if [ -f project_state.md ] || [ -d memories ] || [ -d chapters ]; then
  yes "workspace data found in current directory"
else
  no  "no workspace here yet — create memories/, chapters/, project_state.md"
fi

# ---- Recommendation -----------------------------------------------------------
echo
echo "--------------------------------------------------"
case "$RT" in
  openclaw)          ADAPTER="adapters/openclaw.md";          MSG="OpenClaw detected — it provides C1-C4 natively." ;;
  claude-code)       ADAPTER="adapters/claude-code.md";       MSG="Claude Code detected — use OS scheduler for C3/C4." ;;
  claude-agent-sdk)  ADAPTER="adapters/claude-agent-sdk.md";  MSG="Agent SDK detected — you own the loop; wire C3/C4 in code." ;;
  *)                 ADAPTER="adapters/generic-cron.md";      MSG="No known agent CLI found — use the generic cron+CLI adapter." ;;
esac
echo "Recommended adapter:  deployment/$ADAPTER"
echo "Why: $MSG"

if [ "$RT" != "openclaw" ]; then
  if [ -z "$SCHED" ]; then
    echo "Note: no scheduler found -> run SEMI-AUTO (you open each session). See deployment/README.md (degradation)."
  fi
  if [ -z "$NOTIFY" ]; then
    echo "Note: no notifier found (install curl) -> nudges write to file/console until you add C4."
  fi
fi
echo "Next: open the adapter above and wire C1-C4, then ask the agent 'Where are we with my memoir?'"
echo "--------------------------------------------------"
