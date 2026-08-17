# Codex 11-Tool / Plugin Audit — 2026-08-17

Method: source -> pin -> audit -> sandbox -> smoke test -> approve/reject
(Little Homie software-supply-chain principles, `ops/LITTLE_HOMIE_RULES.md`).

---

## 0. READ THIS FIRST — WHERE THIS AUDIT RAN

**LIVE:** This audit ran in an **ephemeral Linux cloud container**
(Claude Code on the web), not on the Windows Codex host.

- Audit host: Linux `x86_64`, `root`, repo at `/home/user/wealth-machine`.
- Codex host: **Windows**, `C:\Users\Olivia\wealth-machine` (per
  `ops/SESSION_STATE.md` and `last_frame.png`).

Consequences, stated plainly:

1. **No Windows state was read or changed by this audit.** Nothing here
   verifies or modifies the Windows Codex configuration. Claims about the
   Windows host would be guesses, so none are made.
2. **Nothing was installed onto the Codex host.** Packages fetched during
   this audit live in a scratch directory in a container that is destroyed
   when the session ends. That is the sandbox, and it is self-cleaning.
3. **Windows security was not weakened, because Windows was never touched.**
4. The deliverable is therefore an **audit + pinned configuration + rollback
   plan** that the Windows Codex side can apply deliberately — not a set of
   silent installs.

**Egress note:** the audit container routes through a filtering proxy.
`context7.com` and `api.osv.dev` returned `403` on CONNECT. Where that
blocked a check, it is recorded as **NOT VERIFIED HERE** rather than passed.

---

## 1. SECURITY FINDINGS FOUND WHILE AUDITING (not part of the 11)

These outrank every tool decision below.

### FINDING-1 — `wealth-machine` is a PUBLIC repository

Confirmed via GitHub API: `"visibility": "public"`, `"private": false`.

### FINDING-2 — Full Windows desktop screenshots are published publicly

`last_frame.png` and `test_capture.png` are **tracked** in that public repo.
`last_frame.png` was opened during this audit and contains a full desktop
capture: the Codex session window and its command history, a personal chat
conversation, the Windows taskbar, running applications, and the account
name.

This is not a one-off. `portable_agent.py` rewrites `last_frame.png` on every
screenshot command, and the operating loop commits and pushes it. **The
bridge continuously publishes the operator's desktop to the public
internet.** Severity: high, and ongoing until stopped.

### FINDING-3 — `.env` is tracked, but currently holds placeholders

`.env` is committed and there is no `.gitignore`. Values were inspected
structurally only (never printed): lengths 22 / 26 / 18 characters, and none
parse as JWTs. Real Supabase URLs run ~40 chars and real keys 200+, so these
are **placeholders, not live credentials**.

So: **no live secret is currently exposed** — but `lib/supabase_client.py`
reads `SUPABASE_SERVICE_ROLE_KEY` from this file, so the moment a real key is
pasted in, it is one `git commit` away from being public. A service-role key
bypasses Row Level Security, i.e. full database admin.

### Recommended remediation — OWNER GATE (not performed by this audit)

Each of these is destructive or account-level, so none were done:

1. Make the repository **private**, or stop committing screenshots.
2. Untrack the sensitive files. `--cached` keeps local copies, but the
   deletion propagates to the Windows clone on next pull — so run it
   deliberately, when the Windows side is ready:
   ```
   git rm --cached .env last_frame.png test_capture.png
   ```
3. Treat anything ever shown in a pushed screenshot as disclosed.
4. Purge history if any real key was ever committed (`git filter-repo`),
   then rotate the key in the Supabase dashboard.

A preventive `.gitignore` was added by this audit (see §4). Note that
`.gitignore` does **not** untrack already-tracked files — step 2 is still
required.

---

## 2. THE 11 ITEMS

Legend: READY / READY-WITH-RESTRICTIONS / INSTALLED-NOT-READY / OWNER GATE /
DEFERRED / REJECTED / NATIVE-EQUIVALENT.

---

### 1. Playwright — **READY** (audit host) / re-verify on Windows

| Field | Value |
|---|---|
| Version | `playwright` **1.56.1** (latest upstream is 1.62.1 — intentionally NOT upgraded) |
| Source | https://github.com/microsoft/playwright · npm `playwright` |
| License | Apache-2.0 |
| Browser | Chromium **141.0.7390.37**, pre-pinned at `/opt/pw-browsers` |
| Files changed | None in repo. Scratch-dir install only. Added `ops/tooling/playwright_smoke.js` as a reusable test. |
| Config changed | None |
| Permissions | Local process spawn + loopback socket |
| Network | **Loopback only** (`127.0.0.1`, ephemeral port). No external host contacted. |
| Telemetry | None observed |
| Secrets accessed | NO |
| Production touched | NO |
| Cost | $0.00 |
| Advisories | `npm audit`: 0 vulnerabilities (info/low/moderate/high/critical all 0) |
| Rollback | `rm -rf` the scratch dir; delete `ops/tooling/playwright_smoke.js` |

**Smoke test — actually executed, PASS:**
```
LOOPBACK URL: http://127.0.0.1:40561/
BROWSER: 141.0.7390.37
TITLE-BEFORE: CODEX SMOKE TEST
TITLE-AFTER : CLICK-OK
SCREENSHOT BYTES: 7551
SMOKE RESULT: PASS
```
Served a local HTML file over loopback, launched headless Chromium,
navigated, clicked, asserted DOM mutation, captured a screenshot.

**Reason:** Healthy, pinned, permissively licensed, zero advisories, and
verified end-to-end without leaving the machine. Version deliberately held at
1.56.1 per the preserve-the-known-good rule — 1.62.1 would force a browser
re-download and break the offline pin for no gain.

**Caveat:** this PASS is for the **audit container**. The Windows Playwright
install is a separate artifact and was not reachable from here.

---

### 2. Context7 — **READY-WITH-RESTRICTIONS** (surface verified, lookup NOT verified here)

| Field | Value |
|---|---|
| Version | `@upstash/context7-mcp` **4.0.2**, published 2026-08-11 |
| Source | https://github.com/upstash/context7 (`packages/mcp`) |
| License | MIT (server). **Backend API, parser and crawler are closed-source.** |
| Files changed | Added `ops/tooling/context7.mcp.json` |
| Config changed | None applied — the file is a template for the Codex host |
| Permissions | Process spawn; outbound HTTPS to `context7.com` |
| Network | `context7.com` only |
| Telemetry | None separate from the API calls themselves |
| Secrets accessed | NO — no API key configured (free tier). Do not add one. |
| Production touched | NO |
| Cost | $0.00 (free tier, no key) |
| Advisories | `npm audit`: 0 vulnerabilities |
| Rollback | Delete the MCP server entry; `npx` cache clear |

**Smoke test — partial, honestly reported:**
```
INIT OK: {"name":"Context7","version":"4.0.2", ...}
TOOLS EXPOSED: resolve-library-id, query-docs
```
A real MCP stdio handshake confirmed the server starts and exposes **exactly
two read-only tools** — no write, shell, or filesystem tool in the surface.

The live documentation call **failed**: `Error searching libraries: TypeError:
fetch failed`. Root cause confirmed as this container's egress policy, not the
tool: `CONNECT tunnel failed, response 403` for `context7.com:443`.

**Therefore Context7 is NOT claimed as fully READY.** Tool surface: verified.
Functional lookup: **NOT VERIFIED HERE** — must be re-tested on the Windows
Codex host, which has normal egress.

**Restriction that must be carried over (this is a real data-egress boundary):**
Context7's own input schema warns:

> "The query is sent to the Context7 API for processing. Do not include any
> sensitive or confidential information such as API keys, passwords,
> credentials, personal data, or proprietary code in your query."

So agent-authored query text **does leave the machine**. Allow library names
and generic topics only. Never paste repository code, `.env` contents, or
Supabase identifiers into a Context7 query. Given FINDING-2, this restriction
is not theoretical.

---

### 3. Supabase Agent Skills / MCP — **OWNER GATE / DEFERRED**

| Field | Value |
|---|---|
| Version | `@supabase/mcp-server-supabase` **0.10.0**, published 2026-08-10 |
| Source | https://github.com/supabase-community/supabase-mcp |
| License | Apache-2.0 |
| Files changed | **None** |
| Config changed | **None** |
| Secrets accessed | NO |
| Production touched | NO |
| Cost | $0.00 |
| Rollback | N/A — nothing installed |

**Not installed. Gate conditions from the brief were not met** — no
non-production project reference was supplied, no confirmation of absent
production data, and OAuth/PAT authorization requires the owner.

**Known advisory (material):** a publicly disclosed prompt-injection class
against this server, where instructions stored *in database rows* caused the
MCP server to read private tables and write results back where the attacker
could read them. Upstream mitigations now exist — `--read-only`, feature
groups, and wrapping SQL results in untrusted-data tags — but these reduce
the blast radius rather than eliminate the class.

**Pre-conditions before this may proceed:** a dedicated throwaway project,
`--read-only`, minimum feature groups, a scoped PAT, and owner-run OAuth.

---

### 4. SkillUI — **REJECTED** (prior REJECT upheld on fresh audit)

| Field | Value |
|---|---|
| Version | https://github.com/modstart-lib/skillui |
| License | Apache-2.0 |
| Stars | **14** |
| Security policy | **None.** Security tab shows 0 items, no advisories, no policy. |
| Files changed | **None** |
| Secrets / production / cost | NO / NO / $0.00 |

**Reason — the prior finding is not fixed, and the architecture is the
finding.** SkillUI one-click-installs skills from the third-party
`skillui.com` marketplace and **automatically syncs them into the rules
directories of AI coding tools**, Codex included.

Skill files are *instructions an agent obeys*. A GUI that writes
marketplace-sourced instructions into Codex's rules directory is a direct
prompt-injection path into an agent that can execute shell commands on the
Windows desktop via `portable_agent.py`. At 14 stars there is effectively no
independent review of that marketplace's contents.

No evidence of a material security fix was found. **Stays REJECTED.**

---

### 5. Strix — **INSTALLED-NOT-READY / OWNER GATE**

| Field | Value |
|---|---|
| Version | `strix-agent` **1.5.3** (PyPI), requires Python >=3.12 |
| Source | https://github.com/usestrix/strix |
| License | Apache-2.0 |
| Files changed | **None** |
| Secrets accessed | NO |
| Production touched | NO |
| Cost | $0.00 |
| Rollback | `pip uninstall strix-agent` on whichever host holds it |

**Two hard blockers, both explicitly owner-gated by the brief:**

1. **Docker required.** Strix runs its tooling in sandbox containers and pulls
   an image on first run. The brief forbids installing Docker or major
   infrastructure without an owner gate.
2. **LLM API key required**, and a real scan means many paid model calls.

No scan was run. No Docker was installed. No credentials were configured.
Status is unchanged from the prior evaluation and correctly so.

---

### 6. LLM Council — **DEFERRED**

| Field | Value |
|---|---|
| Source | https://github.com/karpathy/llm-council |
| License | **NONE — no LICENSE file exists in the repository** |
| Files changed | **None** |
| Secrets / production / cost | NO / NO / $0.00 |

**Reasons:**

1. **No license.** Absent an explicit license, the work is all-rights-reserved
   by default. It fails the license gate on its own.
2. **Paid provider access is the entire function.** It requires
   `OPENROUTER_API_KEY` and fans every query out to several frontier models,
   then runs review and chairman passes on top — several paid calls per
   question. The brief forbids OpenRouter credentials and paid calls.
3. The author describes it as a "99% vibe coded" Saturday hack — fine for what
   it is, not a dependency to route work through.

There is no useful subset that works without paid provider access, so this is
**DEFERRED**, not partially adopted.

---

### 7. OmniRoute — **REJECTED** (prior REJECT upheld)

| Field | Value |
|---|---|
| Candidate | https://github.com/diegosouzapw/OmniRoute (MIT) |
| Files changed | **None** |
| Secrets / production / cost | NO / NO / $0.00 |

**Reason — the credential-boundary failure is structural, not a bug to fix.**

1. **Name collision / provenance risk.** At least four unrelated GitHub
   projects publish under the name "OmniRoute" (`diegosouzapw`, `pitbaden`,
   `0xzapata`, and others). Ambiguous naming across near-identical
   descriptions is a textbook supply-chain hazard: the pin is only as good as
   picking the right repo, and there is no canonical one.
2. **It concentrates every provider credential in one process.** An AI gateway
   holding keys for hundreds of providers is the highest-value single target
   on the machine.
3. **"339 providers, 90+ free" is the risk, not the feature.** Free upstream
   inference is typically financed by training on submitted prompts. Routing
   Codex through it would send repository code to third parties — which the
   brief prohibits without approval.
4. Marketing claims ("450+ contributors", "never phones home") are asserted by
   the same README that asks for every key; the audit found no independent
   verification.

The requested reconsideration conditions — strict allowlists, local binding,
provider restrictions, zero-unapproved-spend — cannot be confirmed against a
project whose identity is itself ambiguous. **Stays REJECTED.**

---

### 8. Claude-Mem — **REJECTED** (prior REJECT upheld)

| Field | Value |
|---|---|
| Version | `claude-mem` **13.15.2**, published 2026-08-16 (very active) |
| Source | https://github.com/thedotmack/claude-mem |
| License | Apache-2.0 |
| Files changed | **None** |
| Secrets / production / cost | NO / NO / $0.00 |

**Partial credit where earned:** telemetry *can* now be disabled, and honours
`DO_NOT_TRACK`, `CLAUDE_MEM_TELEMETRY=0`, and `enabled: false` in
`telemetry.json`. That specific prior finding is materially improved.

**But the disqualifying risks are the product, not the telemetry:**

1. **Broad capture is the core feature.** It captures what the agent does
   across a session — tool calls, outputs, working context. Disabling that
   disables the tool.
2. **It performs its own provider calls.** Observations are compressed via the
   Claude Agent SDK, so using it means ongoing paid model calls, against the
   no-paid-calls rule.
3. **Credential-store access** for those calls was a prior finding and is
   inherent to that design.
4. **Environment-specific amplifier:** captured memory files land in the
   workspace, and this workspace auto-commits and pushes to a **public**
   repo (FINDING-1/2). A session-capture tool here is a publication pipeline.

The brief's bar was "demonstrably removed **or** completely disabled." The
telemetry meets it; the capture and provider calls cannot, since removing them
removes the tool. **Stays REJECTED.**

---

### 9. Headroom — **REJECTED** (prior REJECT upheld)

| Field | Value |
|---|---|
| Version | `headroomlabs-ai/headroom` **v0.35.0**, released 2026-08-13, Apache-2.0 |
| Name collision | PyPI `headroom` is **0.2.7, MIT** — a different project |
| Files changed | **None** |
| Secrets / production / cost | NO / NO / $0.00 |

**Genuine improvements observed:** actively maintained, patches CVEs promptly
(h2 CVE-2026-71554, nltk CVE-2026-54293, aiohttp, cryptography), and now
claims reversible compression (CCR) with "history is never dropped" — which
directly addresses the prior lossy-evidence finding, if true.

**Still disqualifying:**

1. **Beacon traffic still exists.** Release notes reference Beacon telemetry
   with hourly R2 compaction reporting savings metrics, plus a
   `fix(proxy): guard telemetry and TOIN endpoints`. Guarding an endpoint
   confirms the endpoint. The prior beacon finding is **not** resolved.
2. **It is a proxy in front of the model.** Adopting it puts every Codex
   prompt, every tool output, and all repository code through an additional
   process — the broadest possible trust boundary, for a token-cost
   optimisation.
3. **Name ambiguity** across three "headroom" projects with different licenses
   and version lines makes a trustworthy pin difficult.
4. Requires provider API credentials to operate as a proxy.

The compression-integrity claim is plausible but unverified, and the
verification cost exceeds the benefit. **Stays REJECTED.**

---

### 10. Codex-native Claude Code Setup equivalent — **NATIVE-EQUIVALENT / NOT NEEDED**

| Field | Value |
|---|---|
| Files changed | **None** |
| Secrets / production / cost | NO / NO / $0.00 |

Codex already provides these mechanisms natively. Installing a second
framework would duplicate them and add a supply-chain dependency for no
capability gain. Mapping:

| Need | Codex-native mechanism | Status in this repo |
|---|---|---|
| Persistent project instructions | `AGENTS.md` | **GAP — none exists.** `LITTLE_HOMIE.md` + `ops/*.md` do the job by convention, but nothing auto-loads them. |
| Reusable procedures | Skills (`SKILL.md`) | Present under `tools/jarvis/*` |
| External tools | MCP servers | Context7 template added (§2) |
| Long-term memory | `ops/SESSION_STATE.md`, `ops/RESTORE_HANDOFF.md` | LIVE and working |
| Failure memory | `ops/MISTAKE_LEDGER.md` | LIVE and working |
| Permissions | Codex approval prompts | LIVE — visible in `last_frame.png` |
| Delegation | Subagents | Available, unused |

**One recommendation, no install required:** the read-order in
`LITTLE_HOMIE.md` currently depends on the operator remembering it. Promoting
it into an `AGENTS.md` at the repo root would make Codex load the operating
rules automatically. That is a native fix for the only real gap.

---

### 11. Task Observer — **READY-WITH-RESTRICTIONS (adapted)** — needs owner opt-in

| Field | Value |
|---|---|
| Source | `ByronWilliamsCPA/.claude` → `.claude/skills/task-observer/SKILL.md` |
| Upstream author | Eoghan Henn / rebelytics.com ("One Skill to Rule Them All") |
| License | **CC BY 4.0** (attribution required — preserved in the adaptation) |
| Size | 23,117 bytes, pure Markdown |
| Files changed | Added `ops/tooling/task-observer-restricted.md` (spec only, not active) |
| Secrets / production / cost | NO / NO / $0.00 |
| Rollback | Delete the one file |

**This is the only item where a fresh audit changed the picture, so here is
the evidence.** The full skill was fetched and inspected:

- **Network / exfiltration indicators: NONE.** No `curl`, no `fetch`, no
  webhook, no telemetry, no upload. The only URLs are the author's
  attribution link and internal doc references.
- **Git staging / commit indicators: NONE.** Zero matches for
  `git`/`commit`/`stage`/`push`. It does not auto-stage anything.
- **Writes:** one local observation-log Markdown file in the workspace.
- **Executable code: none.** It is instructions, not a program.

So "automatic staging" and "unrestricted history capture to a service" are
**not** properties of this skill. Two real concerns remain:

1. **Silent always-on capture.** The skill says to append observations
   "**silently** during the session", is marked `user-invocable: false`, and
   asks to be auto-invoked at the start of *every* task session via a
   config-level instruction. That is exactly the always-on, non-opt-in
   behaviour the brief rules out.
2. **Environment-specific:** its log file would land in a workspace that
   auto-commits to a **public** repo.

**Both are fixable, and the adaptation in
`ops/tooling/task-observer-restricted.md` fixes them:** explicit invocation
only (no session-start hook, no `AGENTS.md` auto-trigger), no silent logging
(each write announced), log path gitignored, and no autonomous action.

**Status is READY-WITH-RESTRICTIONS as a written spec — it is NOT active.**
Enabling it is the owner's call.

---

## 3. TOTALS

| Metric | Result |
|---|---|
| **TOTAL ADDED COST** | **$0.00** — no paid API call, subscription, or model call was made |
| **PRODUCTION TOUCHED** | **NO** — no Supabase project, no live database, no production system |
| **SECRETS EXPOSED** | **NO** by this audit. `.env` was inspected structurally only; no value was printed, logged, or transmitted. Pre-existing exposure documented in §1 — see FINDING-2 (desktop screenshots), which is real and ongoing. |
| **WINDOWS SECURITY WEAKENED** | **NO** — the Windows host was never contacted. No Windows setting, policy, or credential was read or altered. |
| **OAUTH / ACCOUNT AUTH PERFORMED** | **NO** |
| **DOCKER / INFRASTRUCTURE INSTALLED** | **NO** |
| **PRIVATE CODE SENT EXTERNALLY** | **NO** |
| **ROLLBACK CONFIRMED** | **YES** — see §4 |

### Final status of the 11

| # | Item | Status |
|---|---|---|
| 1 | Playwright | **READY** (verified by executed smoke test) |
| 2 | Context7 | **READY-WITH-RESTRICTIONS** (surface verified; lookup blocked here) |
| 3 | Supabase MCP | **OWNER GATE / DEFERRED** |
| 4 | SkillUI | **REJECTED** |
| 5 | Strix | **INSTALLED-NOT-READY / OWNER GATE** |
| 6 | LLM Council | **DEFERRED** (also: no license) |
| 7 | OmniRoute | **REJECTED** |
| 8 | Claude-Mem | **REJECTED** |
| 9 | Headroom | **REJECTED** |
| 10 | Codex-native equivalent | **NATIVE-EQUIVALENT / NOT NEEDED** |
| 11 | Task Observer | **READY-WITH-RESTRICTIONS** (adapted spec, not active) |

Net change from the prior evaluation: **one item moved** — Task Observer, from
DEFERRED to READY-WITH-RESTRICTIONS, on the strength of a full source read.
Every other prior status was independently re-derived and confirmed. The
audit was not run to raise the count.

---

## 4. ROLLBACK

**Everything this audit added is four files. Complete removal:**

```
git rm ops/TOOL_AUDIT_2026-08-17.md \
       ops/tooling/context7.mcp.json \
       ops/tooling/playwright_smoke.js \
       ops/tooling/task-observer-restricted.md \
       .gitignore
git commit -m "Roll back tool audit"
```

Or discard the branch entirely:
```
git checkout master
git branch -D claude/codex-11-tool-audit-uyrxlh
```

**No rollback is needed for anything else**, because nothing else was
changed: no tool was installed onto the Codex host, no Codex configuration
was modified, no service was enabled, no credential was created, no package
was added to any persistent environment. Packages fetched during the audit
exist only in a container scratch directory that is destroyed with the
session.

---

## 5. SINGLE BEST NEXT MOVE

Not a tool install. **FINDING-2** — the public repo is receiving desktop
screenshots on an ongoing basis.

Window: **Controller PowerShell**

```powershell
Set-Location C:\Users\Olivia\wealth-machine
git log --oneline -- last_frame.png | Measure-Object -Line
```

That prints how many times a desktop screenshot has been pushed publicly.
Decide on repo visibility from that number before adopting anything new.
