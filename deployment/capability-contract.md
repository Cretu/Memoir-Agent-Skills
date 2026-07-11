# Capability Contract — what the memoir agent needs from any host

The memoir skills are runtime-agnostic markdown. Only the **driving layer**
(`memoir-orchestrator` + `memoir-coach`) needs anything from the host, and only **four**
things. Any agent runtime that can provide these four can run this memoir agent; the
per-runtime [adapters](adapters/) just show *how* each one spells them out.

## The four capabilities

| # | Capability | What it powers | If the host lacks it |
|---|------------|----------------|----------------------|
| **C1** | **File read/write** in a workspace | The whole data model: `memories/`, `chapters/`, `chapter_outline.md`, `memories/style_guide.md`, `project_state.md` | Hard requirement — no workspace, no memoir |
| **C2** | **Skill discovery** (load `SKILL.md` instructions) | Loading the 6 skills' behaviour into the agent | Degrade: paste the skill bodies into the system prompt |
| **C3** | **Scheduled invocation** (run the agent unattended at a time/interval) | Proactive nudges: the daily task, the weekly review | Degrade to **semi-auto**: no autonomous push; the writer opens each session |
| **C4** | **Outbound notification** (send a message to the writer) | Delivering the nudge where the writer will actually see it | Degrade: write the nudge to a file/console; the writer pulls it |

**C1 is mandatory.** C2 makes it clean. **C3 + C4 together are what "drive me" means** —
they are the only reason this is more than a reactive toolbox. A runtime without C3/C4 still
*runs* the memoir; it just can't *initiate*.

## What each adapter must answer
Every adapter in [`adapters/`](adapters/) fills in these blanks:

- **C1 — workspace**: where does the workspace live, and how does the agent read/write files in it?
- **C2 — skills**: where do skills live / how are they discovered? how do the abstract
  `allowed-tools` names (`read_file`, `write_file`, `list_directory`, `text-generation`,
  `memory`) map to this runtime's real tools? any `description`/format limits?
- **C3 — schedule**: what fires the agent unattended, and how do you register a job?
- **C4 — notify**: what channel reaches the writer, and how do you target them?

## The "drive me" contract (C3 + C4), in one sentence
> **On a schedule, run `memoir-orchestrator` in autonomous mode against the workspace, and
> deliver its single short task to the writer's channel.**

Everything platform-specific is just *how you spell that sentence* on a given runtime.

## Tool-name mapping (C2), once for all runtimes
The skills declare abstract tools; map them to whatever the host exposes:

| Abstract (in `allowed-tools`) | Claude Code | OpenClaw / Claude | Agent SDK | Generic |
|-------------------------------|-------------|-------------------|-----------|---------|
| `read_file` | `Read` | file read | your read tool | `cat` / fs read |
| `write_file` | `Write` / `Edit` | file write | your write tool | redirect / fs write |
| `list_directory` | `Glob` / `LS` | list dir | your list tool | `ls` |
| `text-generation` | (implicit) | (implicit) | the model call | the model call |
| `memory` | files in workspace | native memory + files | your store | files in workspace |

## Portable invariants (never change across runtimes)
1. **The data model** — `memories/`, `chapters/`, `chapter_outline.md`,
   `memories/style_guide.md`, `project_state.md`. Identical everywhere; it *is* the agent's
   state, so any runtime's own "memory" feature is optional on top of it.
2. **The safety guarantees live in the skills, not the host** — the Orchestrator's care
   gate, quiet windows, and the truth-contract rule that *a scheduled run never finalizes
   prose*. Keep them intact on every runtime (see `memoir-ethics-and-care.md`).
3. **The skill set and roles** — see `orchestration.md`.

Because the state and the rules are portable, switching runtimes is just swapping the
adapter for C1–C4 — the book, the progress, and the safety behaviour come along unchanged.
