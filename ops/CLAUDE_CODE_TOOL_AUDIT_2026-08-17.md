# Claude Code — 13-Group Tool / Skill Expansion Audit — 2026-08-17

Scope: **Claude Code only.** Codex was not configured. Little Homie production
was not modified.

Companion document: `ops/TOOL_AUDIT_2026-08-17.md` (the Codex-side pass).
Where an upstream finding carries over, it is re-derived here against Claude
Code's actual integration rather than copied.

---

## 0. ENVIRONMENT INVENTORY (done before anything was installed)

| Property | Value |
|---|---|
| Claude Code | **2.1.234**, `/opt/node22/bin/claude` |
| Host | Linux x86_64, root, **ephemeral cloud container** |
| Node / Python / Bun | v22.22.2 / 3.11.15 / 1.3.11 |
| Plugins | **`~/.claude/plugins` does not exist — zero plugins installed** |
| User settings | **No `~/.claude/settings.json`.** Only harness-managed `launcher-settings.json` (SessionStart + Stop hooks, `permissions.allow: ["Skill"]`) |
| Project config | **No `.claude/` in the repo before this task** |
| User MCP servers | **None.** `mcpServers: []` in `~/.claude.json` |
| Harness MCP servers | `github`, `claude-code-remote` (provided, not user-configured) |
| Skills present | 7 Anthropic-synced (`docx`, `pdf`, `pptx`, `xlsx`, `skill-creator`, `morning`, `session-start-hook`) + ~20 built-in (`code-review`, `security-review`, `artifact-design`, `dataviz`, `simplify`, `run`, `init`, …) |
| Playwright | Browsers pre-pinned at `/opt/pw-browsers` (chromium-1194) |

### The fact that shapes every decision below

**This container is ephemeral.** Anything written to `~/.claude/` is destroyed
when the session is reclaimed. Installing into the home directory would
produce a report full of "installed" claims that evaporate.

So everything adopted here was installed into **`.claude/` inside the
repository**, which persists through git. That is the only durable install
target in this environment, and it is why the deliverable is a repo commit
rather than a set of home-directory changes.

### Status of the 13 groups *before* this task

| Group | Before |
|---|---|
| 1 Playwright | Partially available (browsers pre-installed, no npm package) |
| 2 Context7 | **Absent** |
| 3 Supabase MCP | **Absent** |
| 4 SkillUI | **Absent** |
| 5 Strix | **Absent** |
| 6 LLM Council | **Absent** |
| 7 OmniRoute | **Absent** |
| 8 Claude-Mem | **Absent** |
| 9 Claude Code Setup | **Native** |
| 10 Task Observer | **Absent** |
| 11 Headroom | **Absent** |
| 12 Matt Pocock skills | **Absent** |
| 13 HIG Doctor | **Absent** |

Nothing was already installed, so nothing was reinstalled.

---

## 1. PLAYWRIGHT — **READY**

| Field | Value |
|---|---|
| Canonical source | https://github.com/microsoft/playwright · npm `playwright` |
| Exact version | **1.56.1** (latest is 1.62.1 — deliberately not taken) |
| License | Apache-2.0 |
| Installed before | Partially — browsers only |
| Security result | **PASS** — `npm audit` 0 vulnerabilities |
| Files changed | `ops/tooling/playwright_smoke.js` (from the earlier pass, re-verified) |
| Config changed | None |
| Permissions | Local process spawn + loopback socket |
| Network endpoints | **`127.0.0.1` only.** No external host. |
| Telemetry | None observed |
| Secrets accessed | NO |
| Production touched | NO |
| Cost | $0.00 |
| Rollback | `rm -rf` scratch dir; delete the smoke script |

**Smoke test — executed, PASS:**
```
LOOPBACK URL: http://127.0.0.1:39383/
BROWSER: 141.0.7390.37
TITLE-BEFORE: CODEX SMOKE TEST
TITLE-AFTER : CLICK-OK
SCREENSHOT BYTES: 7551
SMOKE RESULT: PASS   (exit 0)
```
Local page → DOM snapshot → selector interaction → text verification →
screenshot, all asserted rather than assumed. No external account or browser
session touched.

**Reason:** pinned at 1.56.1 to match the pre-installed chromium-1194 build.
Upgrading to 1.62.1 would trigger a browser re-download and break the offline
pin for no gain.

---

## 2. CONTEXT7 — **READY-WITH-RESTRICTIONS** (surface verified; lookup blocked here)

| Field | Value |
|---|---|
| Canonical source | https://github.com/upstash/context7 (`packages/mcp`) |
| Exact version | `@upstash/context7-mcp` **4.0.2**, published 2026-08-11 |
| License | MIT (server). Backend API/parser/crawler are **closed-source**. |
| Installed before | NO |
| Security result | **PASS** — `npm audit` 0 vulnerabilities; exactly 2 read-only tools |
| Files changed | `ops/tooling/context7.mcp.json` (template, from the earlier pass) |
| Config changed | **None applied.** Not registered as an MCP server in this container — it would evaporate, and the lookup cannot be verified here anyway. |
| Permissions | Process spawn; outbound HTTPS |
| Network endpoints | `context7.com` only |
| Telemetry | None beyond the API calls themselves |
| Secrets accessed | **NO** — no API key configured; free tier |
| Production touched | NO |
| Cost | $0.00 |
| Rollback | Remove the MCP entry; clear npx cache |

**Smoke test — partial:**
```
INIT OK: {"name":"Context7","version":"4.0.2", ...}
TOOLS EXPOSED: resolve-library-id, query-docs
```
A real MCP stdio handshake confirms exactly **two read-only tools** — no
write, shell, or filesystem tool in the surface.

The live public-documentation lookup **failed**:
`Error searching libraries: TypeError: fetch failed`, root-caused to this
container's egress policy (`CONNECT tunnel failed, response 403` for
`context7.com:443`), not to the tool.

**Not claimed READY**, because READY requires a working functional smoke test
and this one did not complete.

**Restriction (a real egress boundary).** Context7's own input schema states
the query "is sent to the Context7 API" and warns against including API keys,
passwords, credentials, personal data, or proprietary code. Allow library
names and generic topics only.

---

## 3. SUPABASE AGENT SKILLS / MCP — **OWNER GATE / DEFERRED**

| Field | Value |
|---|---|
| Canonical source | https://github.com/supabase-community/supabase-mcp |
| Exact version | `@supabase/mcp-server-supabase` **0.10.0**, published 2026-08-10 |
| License | Apache-2.0 |
| Installed before | NO |
| Files / config changed | **None** |
| Secrets accessed | NO — **no service-role key was requested, per your instruction** |
| Production touched | NO |
| Cost | $0.00 |
| Rollback | N/A — nothing installed |

Gate conditions were not met: no non-production project reference, no
confirmation of absent production data, and OAuth requires you.

**Known advisory:** a disclosed prompt-injection class where instructions
stored *in database rows* caused the server to read private tables and write
results back where an attacker could read them. Upstream mitigations
(`--read-only`, feature groups, untrusted-data wrapping) reduce blast radius
but do not eliminate the class.

**When it does proceed:** project-scoped, `--read-only`, minimum feature
groups, minimum permissions, scoped PAT — never a service-role key.

---

## 4. SKILLUI — **REJECTED / AUDIT FAIL** (fresh Claude-specific audit)

| Field | Value |
|---|---|
| Canonical source | https://github.com/modstart-lib/skillui |
| License | Apache-2.0 |
| Stars | **14** |
| Security policy | **None** — 0 advisories, no policy document |
| Installed before | NO |
| Files / config changed | **None** |
| Secrets / production / cost | NO / NO / $0.00 |

Audited fresh against Claude Code's integration rather than assumed from the
Codex pass — and Claude Code makes it **worse**, not better.

SkillUI one-click-installs skills from the third-party `skillui.com`
marketplace and **automatically syncs them into the rules/skills directories
of AI coding tools, Claude Code included**.

Skill files are instructions an agent obeys. A GUI that writes
marketplace-sourced instructions straight into `~/.claude/skills/` is a direct
prompt-injection path into an agent with Bash, Write, and network access. The
skill-overwrite behaviour you asked about is precisely the mechanism: writing
into the same namespace where trusted skills live, with no signing, no review
gate, and at 14 stars effectively no community scrutiny.

**Stays REJECTED.** No evidence of a material upstream fix.

---

## 5. STRIX — **INSTALLED-NOT-READY / OWNER GATE**

| Field | Value |
|---|---|
| Canonical source | https://github.com/usestrix/strix · PyPI `strix-agent` |
| Exact version | **1.5.3**, requires Python >= 3.12 |
| License | Apache-2.0 |
| Installed before | NO |
| Files / config changed | **None** |
| Secrets / production / cost | NO / NO / $0.00 |
| Rollback | `pip uninstall strix-agent` |

Two hard blockers, both owner-gated by your own rules:

1. **Docker required** — it runs tooling in sandbox containers and pulls an
   image on first run. Not installed automatically.
2. **LLM API key required**, and any real scan means many paid calls.

No scan was run against any target. No Docker installed. No credentials
configured.

---

## 6. LLM COUNCIL — **DEFERRED / OWNER GATE**

| Field | Value |
|---|---|
| Canonical source | https://github.com/karpathy/llm-council |
| License | **NONE — no LICENSE file in the repository** |
| Installed before | NO |
| Files / config changed | **None** |
| Secrets / production / cost | NO / NO / $0.00 |

1. **No license.** Absent an explicit license the work is all-rights-reserved
   by default. It fails the license gate before anything else is considered.
2. **Paid provider access is the whole function.** It requires
   `OPENROUTER_API_KEY` and fans each query across several frontier models,
   then runs review and chairman passes — several paid calls per question.
   **No fully local zero-cost mode exists**, so there is no safe subset to
   evaluate.
3. Author describes it as a "99% vibe coded" Saturday hack.

Your framing is right that council capability suits hard reasoning, not
routine work — but at $0 it cannot run at all.

---

## 7. OMNIROUTE — **REJECTED** (you asked me to try to make it pass; here is what I found)

| Field | Value |
|---|---|
| Canonical source | https://github.com/diegosouzapw/OmniRoute |
| Exact version | **3.8.50**, commit `aa912c42a7d50dd4c87c356f42218ccd2ff42c59` (2026-08-17) |
| License | MIT |
| Installed before | NO |
| **Files / config changed** | **None — nothing was installed** |
| Secrets / production / cost | NO / NO / $0.00 |

I cloned it and audited the source properly rather than judging it from the
README. It is real, MIT, actively developed, and has a genuine SECURITY.md
with a disclosure process. Credit where due.

**It still cannot pass, and the blockers are architectural rather than
configuration — which means there is nothing I can "fix" to clear them.**

**Blocker 1 — the postinstall script executes on install.**
`postinstall: node scripts/build/postinstall.mjs` (455 lines) runs
automatically on `npm install`, and it:
- **downloads prebuilt native binaries** via `node-pre-gyp` using `execSync`;
- **patches `~/.cache/node-gyp/<version>/include/node/common.gypi`** — editing
  the global Node build toolchain configuration *outside* the project
  directory.

Running `--ignore-scripts` blocks this, but then the native modules the app
depends on are left broken by design. There is no configuration that both
installs cleanly and skips this.

**Blocker 2 — TLS-fingerprint impersonation of provider web UIs.**
The postinstall header documents two shipped native modules:
- `wreq-js` — "TLS client for OAuth providers"
- `tls-client-node` — "TLS client for **chatgpt-web / claude-web / grok-web /
  lmarena / perplexity-web**"

Confirmed in source: `src/shared/constants/providers/web-cookie.ts`,
`clientIdentityProfiles.ts`, and `grok-web` / `perplexity-web` in the provider
constants. This is a *web-session* provider mode: it drives providers'
**consumer web interfaces** using impersonated browser TLS fingerprints to
avoid bot detection, authenticated by **your logged-in session cookies**.

That single-handedly breaks three of your stated limits — it requires browser
session access, it routes through providers' consumer properties in a way
their terms generally prohibit for programmatic use, and it puts your own
Anthropic/OpenAI accounts at suspension risk. It is not a toggle; it is a
shipped subsystem.

**Blocker 3 — supply-chain surface.** 79 runtime dependencies, 51 dev,
11,852 files, 275 MB, and 7 package.json files carrying lifecycle scripts.
Auditing that to the standard you set is a project, not a task.

**Blocker 4 — no benefit here at $0.** Claude Code in this environment is
served by Anthropic's managed backend. Pointing it at a gateway requires
either paid provider credentials (violates the $0 target and the credential
gate) or the web-session mode above (prohibited). **There is no configuration
in which OmniRoute improves this Claude Code setup at zero cost.**

**What would have to change for it to pass** — so this is a path, not a wall:
1. Install with `--ignore-scripts` succeeding, with native modules vendored
   or unnecessary;
2. a build with the `*-web` / web-cookie provider subsystem **compiled out**,
   not merely unselected;
3. an explicit provider **and** model allowlist enforced server-side, denying
   by default;
4. binding to `127.0.0.1` only;
5. a hard spend ceiling with no fallback to unapproved routes;
6. owner-supplied credentials for the one approved provider.

Items 1–2 require upstream changes. Until they exist, **REJECTED**.

---

## 8. CLAUDE-MEM — **REJECTED** (fresh Claude-specific audit)

| Field | Value |
|---|---|
| Canonical source | https://github.com/thedotmack/claude-mem |
| Exact version | **13.15.2**, published 2026-08-16 (very active) |
| License | Apache-2.0 |
| Installed before | NO |
| Files / config changed | **None** |
| Secrets / production / cost | NO / NO / $0.00 |

**Credit where earned:** telemetry can now be disabled and honours
`DO_NOT_TRACK`, `CLAUDE_MEM_TELEMETRY=0`, and `enabled: false` in
`telemetry.json`. That specific prior concern is materially addressed.

**Disqualifying for this task anyway:**

1. **It makes provider calls by design.** Observations are compressed via the
   Claude Agent SDK — ongoing paid model calls. That alone fails the **$0
   cost target**, and it cannot be disabled without disabling the tool.
2. **Broad prompt/tool capture is the product**, not an incidental behaviour.
   Removing it removes the feature.
3. **Credential-store access** is inherent to making those calls.
4. **Environment amplifier:** captured memory lands in the workspace, and this
   workspace is a **public** repo with an auto-commit loop (see
   `ops/TOOL_AUDIT_2026-08-17.md` §1). A session-capture tool here is a
   publication pipeline.

Your bar was "removed **or** disabled and VERIFIED." Telemetry clears it; the
provider calls and capture cannot. **REJECTED.**

---

## 9. HEADROOM — **REJECTED**

| Field | Value |
|---|---|
| Canonical source | https://github.com/headroomlabs-ai/headroom |
| Exact version | **v0.35.0**, released 2026-08-13 |
| License | Apache-2.0 |
| Name collision | PyPI `headroom` is **0.2.7, MIT** — a different project |
| Installed before | NO |
| Files / config changed | **None** |
| Secrets / production / cost | NO / NO / $0.00 |

**Improvements observed:** actively maintained, patches CVEs promptly
(h2 CVE-2026-71554, nltk CVE-2026-54293, aiohttp, cryptography), and now
claims reversible compression (CCR) with "history is never dropped".

**Still disqualifying, against your specific tests:**

1. **Beacon/update traffic still exists.** Release notes reference Beacon
   telemetry with hourly R2 compaction reporting savings metrics, plus a
   `fix(proxy): guard telemetry and TOIN endpoints`. Guarding an endpoint
   confirms the endpoint.
2. **Evidence integrity is the core risk, and it is unverified.** You asked
   specifically about lossy compression of evidence and altered shell/error
   context. Headroom sits **between Claude Code and the model**, compressing
   tool output and error text — exactly the material needed for safe
   debugging. The reversibility claim is plausible but unproven, and a
   compression layer that silently drops a stack frame is worse than no
   compression.
3. **Widest possible trust boundary** — every prompt, tool output, and all
   repository code would pass through it, to save tokens.
4. Requires provider credentials to operate as a proxy → fails $0.

**REJECTED.**

---

## 10. CLAUDE CODE SETUP — **NATIVE-EQUIVALENT / NOT NEEDED**

| Field | Value |
|---|---|
| Files / config changed | **None** |
| Secrets / production / cost | NO / NO / $0.00 |

Measured against the inventory in §0, Claude Code already provides every
capability such a framework would add:

| Capability | Native mechanism | Present? |
|---|---|---|
| Project instructions | `CLAUDE.md` / `AGENTS.md` | Available — **not yet used in this repo** |
| Reusable procedures | Skills (`.claude/skills/`) | **Now used** (§12) |
| External tools | MCP servers | Available; `github` + `claude-code-remote` active |
| Permissions | `settings.json` `permissions.allow/deny` | Active |
| Automation | Hooks (SessionStart / Stop / PreToolUse) | Active |
| Delegation | Subagents (`Explore`, `Plan`, `general-purpose`) | Available |
| Memory / continuity | `ops/SESSION_STATE.md`, `ops/RESTORE_HANDOFF.md` | Working |
| Code review | Built-in `/code-review`, `/security-review` | **Present — and better integrated than third-party equivalents** |

Installing a setup framework would duplicate all of this and add a
supply-chain dependency for no capability gain.

**One native gap worth closing, no install required:** the repo has no
`CLAUDE.md`. The read-order in `LITTLE_HOMIE.md` currently relies on the
operator remembering it. Promoting it to a root `CLAUDE.md` would make Claude
Code load the operating rules automatically. Not done here — it edits Little
Homie operating docs, which is outside this task's scope.

---

## 11. TASK OBSERVER — **REVISE / ADAPT** (spec written, not active)

| Field | Value |
|---|---|
| Canonical source | `ByronWilliamsCPA/.claude` → `.claude/skills/task-observer/SKILL.md` |
| Upstream author | Eoghan Henn / rebelytics.com |
| License | **CC BY 4.0** (attribution required and preserved) |
| Size | 23,117 bytes, pure Markdown |
| Installed before | NO |
| Files changed | `ops/tooling/task-observer-restricted.md` (spec only) |
| Secrets / production / cost | NO / NO / $0.00 |
| Rollback | Delete the one file |

Full source was read. Against your specific criteria:

| Criterion | Finding |
|---|---|
| No secret capture | **PASS** — no credential/env access; it explicitly instructs redaction |
| No network | **PASS** — no `curl`, `fetch`, webhook, or telemetry anywhere |
| No autonomous staging | **PASS** — zero references to `git add/commit/push` |
| No repo modification | **PASS** — writes one local log file |
| Scoped logging | **FAIL as shipped** — logs everything, always |
| Not always-on | **FAIL as shipped** — `user-invocable: false` plus a request for a session-start auto-invoke, and it appends "**silently**" |

So the exfiltration fears do not apply; the **always-on, silent** posture does.
Both failures are fixable, and the adaptation in
`ops/tooling/task-observer-restricted.md` fixes them: explicit invocation only,
announced writes, gitignored log path, non-autonomous.

**Not activated** — enabling it is your call. Efficacy is also unmeasured, so
adopting it now would be exactly the "sounds helpful" trap.

---

## 12. MATT POCOCK ENGINEERING SKILLS — **CONDITIONAL** (10 of 35 installed)

| Field | Value |
|---|---|
| Canonical source | https://github.com/mattpocock/skills |
| Exact commit | **`9c9f36ccd3995266cd675468af71639c8dde1ec5`** (2026-08-17), pkg v1.2.3 |
| License | **MIT** (© 2026 Matt Pocock) |
| Installed before | NO |
| Files changed | `.claude/skills/` — 12 files, 112 KB, + `PROVENANCE.md` |
| Config changed | None — Claude Code auto-discovers `.claude/skills/` |
| Permissions | None. Markdown only. |
| Network endpoints | **None** |
| Telemetry | **None** |
| Secrets accessed | NO |
| Production touched | NO |
| Cost | $0.00 |
| Rollback | `rm -rf .claude/skills` |

### A. Security / provenance — **PASS**

| Check | Result |
|---|---|
| Lifecycle scripts (`preinstall`/`install`/`postinstall`) | **NONE** |
| Runtime dependencies | **NONE** (devDeps: changesets only) |
| Published to npm | No — `private: true`; install = copying Markdown |
| Network / exfiltration across all 35 skills | **None found.** The only `curl` references instruct the agent to hit a *local dev server* while debugging. |
| Credential / env access | **None.** `handoff` explicitly instructs redacting API keys and PII. |
| Auto-commit / push / destructive ops | **None** |
| Telemetry | **None** |
| Executable payloads | 3 shell scripts upstream; **none installed** |

**Rejected install mechanism.** Upstream's `scripts/link-skills.sh` was **not
used**. Its own header disclaims it ("not a supported installer"); it
**symlinks** skills so `git pull` silently changes agent behaviour; and it
**`rm -rf`s** name collisions in the destination. Pinned copies were used
instead — satisfying your "pinned/local over uncontrolled auto-updating"
requirement.

### B. Efficacy — measured where objective, honest where not

**Context cost measured.** Only descriptions sit in context; bodies load on
trigger. Across the ten installed: **1,358 bytes ≈ 339 tokens always-on**.
Seven of ten are `disable-model-invocation: true` (**explicit invoke only**),
so they cannot fire on simple work — which is what keeps simple work simple.

**Duplication check against native Claude Code** — the decisive filter:

| Upstream skill | Decision | Reason |
|---|---|---|
| `code-review` | **REJECT — duplicate** | Native `/code-review` + `/security-review` already exist and are integrated with the harness diff and findings UI. Largest description (418 B) for the least marginal value. |
| `research` | **NEUTRAL — skip** | Overlaps native web search and the `Explore` agent. |
| `domain-modeling`, `codebase-design` | **DEFER** | Auto-triggering, large, unproven. |
| `git-guardrails-claude-code` | **REJECT** | Blocks **all** `git push` via a PreToolUse hook — would break this repo's required push workflow. |
| The other 10 | **CONDITIONAL — installed** | No native equivalent; see `PROVENANCE.md`. |

**What was NOT done, stated plainly:** the controlled A/B you specified —
same task, same model, with-skill vs without-skill, scored by a verifier —
**was not run.** Doing it properly requires spawning comparison agents, which
I did not do unprompted. So these skills are **CONDITIONAL, not ADOPT**: they
passed security and duplication review, and their context cost is measured,
but their behavioural benefit is **unproven**.

By your own rule — a skill does not earn permanent trust because it sounds
helpful — calling them ADOPT here would be the error. The remaining
validation step is named in §14.

---

## 13. HIG DOCTOR — **CONDITIONAL** (safe; efficacy genuinely mixed)

| Field | Value |
|---|---|
| Canonical source | https://github.com/raintree-technology/hig-doctor |
| Exact commit | **`8bfa28f76c62d0ad4bf02640f5a195f3267bcf39`** |
| CLI version | `hig-doctor` **2.0.1** |
| License | **MIT** (tooling). HIG reference text is **© Apple Inc.** |
| Installed before | NO |
| Files changed | **None committed** — audited and tested in scratch only |
| Config changed | None |
| Network endpoints | **None from CLI/core** |
| Telemetry | **None in the CLI.** `@vercel/analytics` exists only in the `website/` package (their marketing site), not in anything shipped to you. |
| Secrets accessed | NO |
| Production touched | NO |
| Cost | $0.00 |
| Rollback | Delete the clone; nothing installed globally |

**Canonical successor confirmed** — this is the current project, superseding
the earlier Apple HIG skills repository; it ships the CLI, 14 skills / 156
reference topics, and an MCP server.

### A. Security — **PASS, and unusually strong**

| Check | Result |
|---|---|
| Runtime dependencies | **ZERO** (one optional: `typescript`) |
| Lifecycle install scripts | **NONE** in any workspace package |
| Network calls in CLI/core | **NONE** |
| Credential / env access | **NONE** (all `token` hits are lexer/regex tokens — false positives) |
| `child_process` / shell exec | **NONE** in production code (tests only) |
| Security policy | **SECURITY.md present**, with scope and disclosure timeline |
| Supply-chain tooling | `socket.yml`, `renovate.json`, a dedicated `test/workflow-security.test.mjs` |
| Apple branding | **Clean** — `brand/` holds only HIG-Doctor's own marks; README disclaims affiliation and points to `developer.apple.com` as canonical |

**MCP note:** the only HTTP in the codebase is an *optional* streamable-HTTP
transport in the MCP package that binds to `localhost`. Per your instruction,
**stdio is the mode to use and the HTTP service must not be exposed** — no
owner approval was sought because it was not enabled.

### B. Efficacy — **tested with seeded defects; results are mixed**

I wrote two fixtures: `Bad.tsx` with **6 deliberate, known** HIG/accessibility
defects, and `Good.tsx` as a clean control, then ran the CLI.

| # | Seeded defect | Result |
|---|---|---|
| 1 | `user-scalable=no` blocks pinch-zoom | ✅ **caught** (⚠ concern) |
| 2 | 20×20 px touch target (HIG minimum 44 pt) | ⚠️ **surfaced but not flagged** — Controls reported "**0 concern(s)**" |
| 3 | `<img>` with no `alt` | ✅ **caught** |
| 4 | `<input>` with no label | ❌ **mislabelled `✓ good`** |
| 5 | Low-contrast `#aaaaaa` on white | ✅ **caught** |
| 6 | `onClick` on a `<div>`, no keyboard access | ✅ **caught** |

- **Recall: 4 of 6** flagged as concerns.
- **False positive: 1** — control `#1a1a1a` on `#ffffff` (≈16.9:1, excellent
  contrast) flagged as a concern. Defensible as "prefer semantic colors", but
  misleading if read as a contrast failure.
- **False negative that matters most:** the 20×20 touch target. That is the
  single most objective, clear-cut rule in the whole HIG surface (44 pt
  minimum), it sits in the tool's flagship area, and the category still
  reported zero concerns.

**Architectural finding — it is not a verifier.** Its output literally
contains `## Instructions for AI Evaluator … Rate each category 1-10`. It is a
**detector plus prompt generator**; the actual judgement remains the model's.
So a clean run is *not* evidence of a compliant UI.

**Cost:** ~9.3 KB / **≈2,300 tokens of output for a 2-file project**. On a real
dashboard this scales badly and would dominate context.

**Verdict — CONDITIONAL:**
- **Use** as an advisory checklist generator on UI work, invoked deliberately,
  scoped to changed files.
- **Do not** gate anything on it, and never read "0 concerns" as a pass.
- **Do not** load the 14 skills / 156 topics into always-on context.
- **Treat Apple's live HIG as authoritative** — the embedded snapshot is dated
  **`snapshotDate: 2025-02-02`**, roughly 18 months stale, despite a
  `generated: 2026-07-22` field. Your instinct not to trust the snapshot was
  correct.
- **Licensing nuance for you to note:** MIT covers the tooling; the reference
  text under `skills/*/references/` is Apple's copyrighted content
  redistributed by a third party.

Not installed into the repo — it is a CLI run on demand
(`bunx hig-doctor@2.0.1` / `npx hig-doctor@2.0.1`, pinned), so vendoring a
large tree would buy nothing.

---

## 14. OVERALL SUMMARY

| Metric | Result |
|---|---|
| **TOTAL ADDITIONAL COST** | **$0.00** — no paid model/API call, no subscription, no purchase |
| **PRODUCTION TOUCHED** | **NO** |
| **SECRETS EXPOSED** | **NO** — no credential was read, requested, printed, or transmitted. No service-role key was requested. |
| **WINDOWS SECURITY WEAKENED** | **NO** — no Windows host was contacted; this ran on Linux |
| **AUTO-UPDATES ENABLED** | **NO** — skills installed as pinned copies at an exact commit; upstream's symlink installer was deliberately rejected |
| **ADMIN PRIVILEGES GRANTED** | **NO** |
| **DOCKER / VM INSTALLED** | **NO** |
| **OAUTH / ACCOUNT AUTH** | **NO** |
| **EXTERNAL PUBLICATION / DEPLOY** | **NO** |
| **ROLLBACK CONFIRMED** | **YES** — see below |

### ACTUALLY READY TO USE NOW

1. **Playwright 1.56.1** — READY. Smoke test executed and passed, exit 0.
2. **10 Matt Pocock skills** — installed, security-cleared, pinned;
   **CONDITIONAL** pending efficacy validation.
3. **Native Claude Code capabilities** — already present and confirmed by
   inventory: `/code-review`, `/security-review`, skills, hooks, MCP,
   permissions, subagents.

### OWNER GATES REMAINING

| Item | Blocked on |
|---|---|
| Supabase MCP | Non-production project ref + confirmation of no production data + your OAuth |
| Strix | Docker installation + an LLM API key (paid) |
| LLM Council | OpenRouter credentials + paid calls (no zero-cost mode exists) |
| Context7 | Nothing from you — needs re-testing where egress permits |
| HIG Doctor MCP over HTTP | Your approval; **stdio is sufficient, so do not enable it** |

### REJECTED

| Tool | Core reason |
|---|---|
| **SkillUI** | Writes third-party marketplace instructions into the agent's own skills directory |
| **OmniRoute** | Postinstall downloads binaries and patches the global node-gyp cache; ships TLS-impersonation of provider **web sessions**; no $0 benefit |
| **Claude-Mem** | Provider calls are intrinsic → fails the $0 target; broad capture is the product |
| **Headroom** | Beacon traffic persists; unverified compression of the exact evidence needed for safe debugging |
| **`code-review`** (Pocock) | Duplicates a stronger native Claude Code capability |
| **`git-guardrails`** (Pocock) | Blocks all `git push`; breaks this repo's workflow |

### NATIVE CAPABILITIES THAT MADE A PLUGIN UNNECESSARY

| Native | Made unnecessary |
|---|---|
| `/code-review`, `/security-review` | Pocock `code-review`; third-party review plugins |
| Skills + `.claude/skills/` auto-discovery | SkillUI's entire purpose |
| MCP client (stdio) | Bespoke tool-integration frameworks |
| Hooks (SessionStart/Stop/PreToolUse) | Task Observer's auto-invoke mechanism; git guardrails |
| `settings.json` permissions | Third-party permission managers |
| Subagents (`Explore`, `Plan`) | Pocock `research`; multi-agent orchestration add-ons |
| `CLAUDE.md` / `AGENTS.md` + `ops/*.md` | "Claude Code Setup" frameworks entirely |
| Built-in context compaction | Headroom |

### ROLLBACK

```
rm -rf .claude/skills          # removes all 10 installed skills + provenance
git rm ops/CLAUDE_CODE_TOOL_AUDIT_2026-08-17.md
```
Or discard the branch: `git checkout master && git branch -D claude/codex-11-tool-audit-uyrxlh`

Nothing else needs unwinding: no global install, no hook, no MCP server, no
binary, no credential, no service, no system setting.

### THE ONE REMAINING VALIDATION STEP

The ten installed skills are **CONDITIONAL, not ADOPT.** To promote them,
run the A/B you specified: same task, same model, same permissions, once
without `.claude/skills/` and once with, scored on correctness, tool calls,
retries, tokens, and side effects. Start with `diagnosing-bugs` and `tdd` —
they are the two that auto-trigger, so they carry the most regression risk.

If a skill adds ceremony to simple work, delete it. Heavy procedure should be
proportional to task risk.
