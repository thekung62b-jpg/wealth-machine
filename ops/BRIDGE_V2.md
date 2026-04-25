# Bridge V2 Runbook

Status labels:
- LIVE means currently safe to use.
- TESTED means proven end-to-end in this workspace.
- PARTIAL means useful but not reliable enough to build on.
- FAILED means do not repeat without a new fix.
- IDEA means not implemented or not proven.

## Current Status

- TESTED: `portable_agent.py` runs from `C:\Users\Olivia\wealth-machine`.
- TESTED: queued shell commands execute through `commands.json`.
- TESTED: screenshot commands update `last_frame.png`.
- TESTED: `output.json` updates after executed commands.
- TESTED: `.openclaw_bridge_state.json` updates after executed commands.
- TESTED: `ops\bridge_smoke_test.py` proves screenshot -> shell -> output/state/frame.
- LIVE: browser page can be opened through the shell-command bridge path.
- LIVE: `ops\browser_helper.py probe` is the preferred browser/window probe path.
- PARTIAL: built-in browser commands inside `portable_agent.py`.
- FAILED: relying on `browser_probe` as a built-in bridge action until runtime dispatch is proven.

## Rule Zero

Use one window label per instruction. Do not combine Bridge PowerShell, Controller PowerShell, Browser, and Codex Terminal steps in one unlabeled block.

## Start Bridge Agent

Window: Bridge PowerShell

```powershell
Set-Location C:\Users\Olivia\wealth-machine
$token = (Get-Content C:\OpenClawBridge\.github_token -Raw).Trim()
python .\portable_agent.py "$token"
```

Expected result:
- The window stays open.
- It prints that the neural link is active.
- The GitHub token stays local and is never pasted into chat.

## Queue One Safe Shell Command

Window: Controller PowerShell

```powershell
Set-Location C:\Users\Olivia\wealth-machine
$id="cmd_echo_$((Get-Date).ToString('yyyyMMddHHmmss'))"
python .\ops\bridge_send_command.py "echo hello_from_bridge" --id $id --os windows --host "$env:COMPUTERNAME" --replace
```

Window: Controller PowerShell

```powershell
Start-Sleep -Seconds 8
python .\ops\bridge_result_check.py
```

Pass condition:
- `output.json` has the same `id`.
- `status` is `done`.
- `stdout` contains `hello_from_bridge`.

## Run Smoke Test

Window: Desktop PowerShell

```powershell
Set-Location C:\Users\Olivia\wealth-machine
python .\ops\bridge_smoke_test.py
```

Pass condition:
- Every line that matters says `PASS`.
- Final line says screenshot -> shell -> output/state/frame changed.

Failure rule:
- If screenshot fails with `screen grab failed`, rerun from the live desktop PowerShell, not a headless or sandboxed terminal.

## Open Local Bridge Page

Window: Controller PowerShell

```powershell
Set-Location C:\Users\Olivia\wealth-machine
$id="cmd_open_bridge_$((Get-Date).ToString('yyyyMMddHHmmss'))"
python .\ops\bridge_send_command.py 'cmd /c start "" "file:///C:/Users/Olivia/wealth-machine/bridge.html"' --id $id --os windows --host "$env:COMPUTERNAME" --replace
```

Window: Browser

Confirm that `bridge.html` is visible before continuing.

## Browser Probe Through Proven Shell Path

Window: Controller PowerShell

```powershell
Set-Location C:\Users\Olivia\wealth-machine
$id="cmd_browser_helper_probe_$((Get-Date).ToString('yyyyMMddHHmmss'))"
python .\ops\bridge_send_command.py "python .\ops\browser_helper.py probe" --id $id --os windows --host "$env:COMPUTERNAME" --replace
```

Window: Controller PowerShell

```powershell
Start-Sleep -Seconds 8
python .\ops\bridge_result_check.py
```

Pass condition:
- `output.json` has the same `id`.
- `status` is `done`.
- `stdout` contains JSON with `ok:true`, foreground `title`, foreground `process_name`, and screenshot metadata.
- `last_frame.png` updates.

## Stop Conditions

- Stop if `ops\bridge_result_check.py` prints `STALE`, `MISSING`, or `FAILED`.
- Stop if `output.json` shows an older command id after waiting; the new command did not execute yet.
- Stop after the same failure happens twice; write the failure to `ops\MISTAKE_LEDGER.md` before trying another approach.
- Stop before destructive commands, credential handling, installs, or broad rewrites unless Big Homie explicitly approves.
