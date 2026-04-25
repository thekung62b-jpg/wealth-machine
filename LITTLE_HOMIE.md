# Little Homie Start Here

Purpose: make Little Homie easier to resume, operate, and recover.

## Read Order

1. `ops\LITTLE_HOMIE_RULES.md`
2. `ops\SESSION_STATE.md`
3. `ops\BRIDGE_V2.md`
4. `ops\MISTAKE_LEDGER.md`
5. `ops\RESTORE_HANDOFF.md`

## Current Best Path

- TESTED: screenshot + shell + output/state/frame smoke test.
- LIVE: use bridge shell commands for safe actions.
- LIVE: use `python .\ops\browser_helper.py probe` for browser/window state.
- PARTIAL: browser control beyond probe/open-page.
- FAILED: built-in `browser_probe` dispatcher path until newly proven.

## Operating Rule

Give Big Homie one short, labeled step at a time. Every command must name the exact window first.

## Recovery Rule

If a session resets or crashes, start with `ops\RESTORE_HANDOFF.md` and do not retry old failures until `ops\MISTAKE_LEDGER.md` has been checked.

## Result Rule

Before interpreting `output.json`, run `python .\ops\bridge_result_check.py`.
