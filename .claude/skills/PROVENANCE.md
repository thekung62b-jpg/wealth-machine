# Installed Skills — Provenance & Pin Record

Maintained per the software-supply-chain rule: record the exact source and
version of everything accepted, and never allow surprise updates.

## Source

| Field | Value |
|---|---|
| Upstream | https://github.com/mattpocock/skills |
| Package name | `mattpocock-skills` v1.2.3 (`private: true` — not published to npm) |
| **Pinned commit** | `9c9f36ccd3995266cd675468af71639c8dde1ec5` |
| Commit date | 2026-08-17 |
| License | MIT (© 2026 Matt Pocock) |
| Install method | **Pinned file copy** — deliberately NOT symlinks |

## Why copies and not `scripts/link-skills.sh`

Upstream ships `scripts/link-skills.sh`. It is **not used here**, for three
reasons found during the audit:

1. **The author disclaims it.** Its own header says it is "a dev-only script,
   intended for use by maintainers of this repo. It is not a supported
   installer."
2. **It creates symlinks into a git clone**, so any `git pull` silently
   changes agent behaviour — an uncontrolled auto-update path.
3. **It `rm -rf`s name collisions** in the destination skills directory, which
   would delete an existing same-named skill without asking.

Copies at a pinned commit avoid all three. The cost is that updates are
manual — which is the intended trade.

## Upgrade procedure (manual, never automatic)

```
git -C <clone> fetch && git -C <clone> log --oneline 9c9f36c..origin/main -- skills/
```
Review the diff for the installed skills only, then re-copy and update the
commit hash above. Do not pull blind.

## What was installed and why

Ten of the 35 upstream skills. Selection favours skills with **no stronger
native Claude Code equivalent**, and prefers explicit invocation.

| Skill | Invocation | Reason |
|---|---|---|
| `grill-me` | explicit | Interview a plan before building. No native equivalent. |
| `grilling` | auto | Engine behind `grill-me`; required by it. |
| `grill-with-docs` | explicit | Same, grounded in supplied docs. |
| `diagnosing-bugs` | auto | Tight reproduce-first debugging loop. No native equivalent. |
| `tdd` | auto | Red-green-refactor discipline. No native equivalent. |
| `to-spec` | explicit | Turn a rough idea into a written spec. |
| `to-tickets` | explicit | Split a spec into tracked units of work. |
| `implement` | explicit | Execute an agreed spec. |
| `handoff` | explicit | Session handoff summary; instructs redaction of secrets. |
| `wayfinder` | explicit | Plan work larger than one session. |

**Always-on context cost: ~1,358 bytes (~339 tokens)** across all ten — only
the descriptions sit in context; bodies load on trigger.

## Deliberately NOT installed

| Skill | Reason |
|---|---|
| `code-review` | **Duplicates native Claude Code `/code-review` and `/security-review`.** The native ones are integrated with the harness diff and findings UI. |
| `research` | Overlaps native web search / Explore agent. |
| `domain-modeling`, `codebase-design`, `improve-codebase-architecture` | Large, auto-triggering, and unvalidated. Candidates for a later pass after efficacy testing. |
| `git-guardrails-claude-code` | Installs a PreToolUse hook that blocks **all** `git push`. Would break this repo's required push workflow. |
| `setup-matt-pocock-skills` | Its purpose is to install the whole collection and write repo config — the uncontrolled path this record exists to avoid. |
| `ask-matt`, `wizard`, `prototype`, `triage`, `teach`, everything in `in-progress/` | Not requested, unproven, or explicitly work-in-progress upstream. |

## Modifications made to upstream files

- **`agents/openai.yaml` removed** from every installed skill. Those files are
  Codex-targeted metadata; this task is Claude Code only and must not
  configure Codex. They are inert for Claude Code, so removing them changes
  no behaviour.
- **`diagnosing-bugs/scripts/hitl-loop.template.sh` removed.** An executable
  payload that nothing in the installed set requires.
- No SKILL.md content was altered.

## Note on `CONTEXT.md`

`diagnosing-bugs` and `tdd` both reference `CONTEXT.md`. This is **not** a
broken link — both guard it with "if it exists", and it refers to an optional
convention file in the *consuming* project, not upstream. Absent here, the
skills degrade gracefully.

## Rollback

```
rm -rf .claude/skills
```
Nothing else is affected: no hook, no setting, no MCP server, no binary, and
no dependency was added.

## Status

**CONDITIONAL** — security-audited and installed, but **not yet
efficacy-validated** by controlled A/B comparison. See
`ops/CLAUDE_CODE_TOOL_AUDIT_2026-08-17.md` §12. Treat as on probation: if a
skill adds ceremony to simple work, remove it.
