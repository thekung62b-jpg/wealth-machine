# Mistake Ledger

Purpose: prevent repeated failed loops.

## Rules

- If the same failure happens twice, stop.
- Label the failure here before trying another approach.
- Prefer the smallest proven path over debugging an unproven path.
- Always verify `output.json` command `id` matches the command just queued.

## Entries

### FAILED: built-in `browser_probe` dispatch

Observed:
- `portable_agent.py` contained `def browser_probe()`.
- `portable_agent.py` contained `elif action == "browser_probe"`.
- Runtime still treated `browser_probe` and `browser_probe ` as raw shell commands.

Impact:
- Do not spend more time on built-in browser dispatch until there is a fresh, isolated runtime proof.

Replacement path:
- Use `python .\ops\browser_helper.py probe` through the already-tested shell-command bridge path.

### FAILED: interpreting stale `output.json`

Observed:
- A newly queued command did not execute within the wait window.
- `output.json` still showed an older command id.

Impact:
- Do not treat old output as the result of the latest command.

Prevention:
- Every queued command must use a unique id.
- Run `python .\ops\bridge_result_check.py`.
- Do not interpret status, stdout, or stderr unless it prints `MATCH`.

### FAILED: nested quoting in bridge commands

Observed:
- Complex nested Python one-liners were split by PowerShell before `bridge_send_command.py` received them.

Impact:
- Avoid nested one-liners when a local helper script can do the same job.

Prevention:
- Put reusable logic into `ops\*.py`.
- Queue simple commands like `python .\ops\browser_helper.py probe`.

### PARTIAL: screenshot from non-desktop terminal

Observed:
- Screenshot capture can fail with `screen grab failed` outside the live desktop context.

Impact:
- Do not use a headless/sandboxed terminal as proof that live desktop screenshot is broken.

Prevention:
- Run `ops\bridge_smoke_test.py` from Desktop PowerShell when validating screen capture.
