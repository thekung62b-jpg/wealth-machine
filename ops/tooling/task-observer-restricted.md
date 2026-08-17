# Task Observer — Restricted Adaptation (SPEC ONLY, NOT ACTIVE)

Status: **READY-WITH-RESTRICTIONS — awaiting owner opt-in. Nothing here is
running.** Audited 2026-08-17, see `ops/TOOL_AUDIT_2026-08-17.md` item 11.

**Attribution:** adapted from "Task Observer" / "One Skill to Rule Them All"
by **Eoghan Henn / rebelytics.com**, licensed **CC BY 4.0**. This adaptation
is a derivative work; attribution is required and retained here.
Upstream: `ByronWilliamsCPA/.claude` → `.claude/skills/task-observer/SKILL.md`.

---

## Why adapt instead of installing upstream as-is

The upstream skill audited clean on the things that usually kill a tool:

- **No network calls.** No `curl`, `fetch`, webhook, upload, or telemetry.
- **No git automation.** Zero references to staging, committing, or pushing.
- **No executable code.** 23KB of Markdown instructions.
- **Writes one file:** a local observation log in the workspace.

Two problems remain, and both are about *how* it runs rather than *what it
sends*:

1. **Silent always-on capture.** Upstream instructs the agent to append
   observations "silently" during the session, is marked
   `user-invocable: false`, and asks to be auto-invoked at the start of every
   task session through a config-level instruction. Logging the operator's
   work without a visible signal is the behaviour the operating rules reject.
2. **This workspace publishes what it writes.** `wealth-machine` is a public
   repo and the operating loop auto-commits. Upstream's default log location
   would be pushed to the internet.

The restrictions below fix both without touching what makes the skill useful.

---

## The four restrictions (all mandatory)

### R1 — Explicit invocation only

- **Do NOT** add a session-start hook.
- **Do NOT** add an auto-invoke line to `AGENTS.md`, `CLAUDE.md`, or any
  project instruction file.
- **Do NOT** set the skill to load on every task session.
- It runs when the operator asks for it by name, and not otherwise.

This reverses upstream's central "Recommended Activation Setup" section. That
section exists to make the skill fire reliably; here, reliability of firing is
exactly what must not be automatic.

### R2 — No silent logging

Upstream's "append silently" instruction is **removed**. Every write is
announced in one line:

```
[task-observer] logged observation #<n> -> <path>
```

The operator can always see that they are being observed, and what was
recorded. An observation the operator would object to seeing announced is an
observation that should not be written.

### R3 — Log path is local and gitignored

- Log location: `ops/.observations/log.md`
- `ops/.observations/` is listed in `.gitignore`.
- **Never** commit, stage, or push the observation log.
- **Never** write it to `VAULT/`, or anywhere the bridge sweeps up.

Given that this repo publishes desktop screenshots publicly, an
observation log about the operator's working patterns must not join them.

### R4 — Non-autonomous

The skill may **record** and **suggest**. It may not act:

- No editing other skills.
- No modifying `AGENTS.md`, `CLAUDE.md`, or `ops/*.md`.
- No queuing bridge commands.
- No autonomous "weekly review" that rewrites files on a schedule.

Any change it proposes is presented to the operator as a suggestion and
applied only on explicit approval — consistent with
`ops/LITTLE_HOMIE_RULES.md` autonomy boundaries.

---

## What is intentionally kept

- The observation-capture idea: noticing repeated corrections and workflow
  patterns worth turning into a documented procedure. That is a genuinely
  good fit for a project that already keeps `ops/MISTAKE_LEDGER.md`.
- The numbered-observation log format and its write-time collision check.
- The distinction between an open observation and an integrated one.

## Relationship to existing practice

This overlaps `ops/MISTAKE_LEDGER.md`, which already records failures so they
are not repeated. Task Observer's addition is capturing *successful* patterns
too, not only failures. If that turns out to be noise in practice, prefer the
mistake ledger and drop this — the smaller proven path wins, per the
operating rules.

---

## Enabling it (owner decision, not automatic)

1. Read the upstream skill in full.
2. Confirm R1–R4 are acceptable.
3. Create `ops/.observations/` (already gitignored).
4. Install the skill file with the R1/R2 edits applied — the
   activation-setup section deleted, and "silently" replaced by the announced
   write from R2.
5. Verify: run one session, confirm the announcement line appears and that
   `git status` shows **no** new tracked file.

**Rollback:** delete the skill file and `ops/.observations/`. Nothing else is
affected — there is no service, daemon, credential, or config entry to unwind.
