# Contributing

Thanks for helping people get their life stories written. This project is a set of
markdown agent skills plus a thin deployment layer — contributions are mostly *writing
and design*, validated by a small amount of tooling.

## Ground rules

1. **Safety invariants are not negotiable.** The care gate, quiet windows, the
   trauma-informed recall rules, and the truth contract ("a scheduled run never
   finalizes prose") are the product. PRs that weaken them will not be merged;
   PRs that strengthen them are especially welcome. See `memoir-ethics-and-care.md`.
2. **The writer owns the words.** Skills propose; the writer approves. Keep that
   stance in any new skill or example.
3. Be kind in reviews. This repo touches grief, family, and memory — the same
   care we ask of the skills applies to contributors.

## Repo layout (what goes where)

| Path | Contents |
|------|----------|
| `memoir-*/` | One skill per directory: `SKILL.md` (instructions) + `SKILL.yaml` (metadata) |
| `memoir-*/references/` | Deep-dive reference docs for the skill |
| `memoir-*/examples/` | Worked interaction examples |
| `memoir-*/templates/` | Prompt sets / output templates |
| `deployment/` | Runtime-agnostic deployment: capability contract + adapters + detector |
| `orchestration.md` | How the skills coordinate (roles, file contracts, phases) |
| `project_state.md` | Progress-ledger template the Orchestrator maintains |
| `scripts/` | Repo tooling (validator) |

## Skill conventions (enforced by CI)

- `SKILL.md` frontmatter must have `name` (== directory name) and `description`
  **≤160 bytes** (OpenClaw's hard limit; good hygiene everywhere).
- Support files live under `references/`, `examples/`, `templates/` — not loose
  in the skill root.
- Every skill has a `SKILL.yaml` with matching `name`.
- Relative markdown links must resolve.
- New skills should be registered in `.claude/skills.json` and given a row in
  `orchestration.md`'s terminology + file-contract tables.

Run the checks locally before pushing:

```sh
make validate     # or: python3 scripts/validate.py
```

## Adding a new skill

1. Copy the shape of an existing skill (e.g. `memoir-coach/`).
2. Define its **file contract** (what it reads/writes) and add it to
   `orchestration.md`.
3. State how it interacts with the Orchestrator (who routes to it, and when).
4. Address the safety implications explicitly in the skill text if it touches
   recall, real people, or autonomous behaviour.
5. `make validate`, then open a PR.

## Adding a deployment adapter

An adapter is a markdown file in `deployment/adapters/` that answers the four
capability questions (C1–C4) from `deployment/capability-contract.md` for one
runtime, and preserves the safety rules. Add a row to the matrix in
`deployment/README.md` and, if detectable, a probe to `detect-runtime.sh`.

## Pull requests

- Keep PRs scoped to one concern; describe the *why*, not just the diff.
- CI must be green (`validate` + ShellCheck + detector smoke run).
- Update `CHANGELOG.md` under **Unreleased** for user-visible changes.
