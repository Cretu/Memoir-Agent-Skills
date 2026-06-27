# Adapter: Other frameworks (capability mapping)

> Part of the runtime-agnostic [deployment layer](../README.md). For agent frameworks that
> aren't covered command-by-command, this maps the four host capabilities
> ([contract](../capability-contract.md)) onto their native concepts. The pattern is always
> the same: **the skills become prompts/nodes, `project_state.md` stays the shared state, and
> the framework supplies C1/C3/C4.** Once you can answer C1–C4, you have an adapter.

## The universal recipe
1. **C1** — give the agent file access to a workspace holding the data model.
2. **C2** — load each `SKILL.md` body as a prompt/template/node; the **Orchestrator** becomes
   the router that reads `project_state.md` and picks the next skill.
3. **C3** — use the framework's scheduler/trigger (or an external cron) to invoke the
   Orchestrator unattended.
4. **C4** — use a messaging node/tool to deliver its one short task to the writer.
5. Port the safety rules (care gate, quiet windows, no-finalize-on-schedule) into the prompts.

## Quick mappings

| Framework | C1 files | C2 skills | C3 schedule | C4 notify | Notes |
|-----------|----------|-----------|-------------|-----------|-------|
| **LangGraph** | file tools / a state field | each skill = a node or prompt; Orchestrator = a router node | external cron/Airflow hits the graph; or a scheduled run | a tool node that posts to a channel | Graph state can mirror `project_state.md`, but keep the file as the durable copy |
| **OpenHands** | native file ops | skills as microagents/prompt files | external cron invoking a headless task | a shell/tool call (curl) | Strong C1; you supply C3/C4 |
| **Dify** | knowledge/files + variables | skills as prompt blocks in a workflow | built-in **schedule trigger** | built-in messaging/HTTP nodes | Mostly no-code; map state to workflow variables + a stored file |
| **n8n / Make** | a file/store node | skills as prompt nodes feeding an LLM node | built-in **cron trigger** | Telegram/Slack/email nodes | Great for C3/C4; weakest at rich C1 — back it with a real file store |
| **AutoGen / CrewAI** | file tools | skills → agent role prompts; Orchestrator = the manager/coordinator agent | external scheduler | a tool that messages the writer | Multi-agent maps cleanly onto the skill roles |

## What stays constant
- `project_state.md` is the **single source of truth** for progress — even where the
  framework has its own state, persist to this file so the project survives restarts and can
  move between runtimes.
- The **Orchestrator's routing logic** and the **safety guarantees** are framework-independent
  — they're in the skill text, not the wiring.
- If a framework can't do C3/C4, you still get a fully functional **semi-auto** memoir agent
  (the writer initiates each run); see the [deployment README](../README.md) on degradation.
