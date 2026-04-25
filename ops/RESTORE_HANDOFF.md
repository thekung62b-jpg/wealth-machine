# Restore And Handoff Brief

Use this after resets, crashes, new sessions, or confusion.

## Current Known State

- TESTED: `portable_agent.py` runs from `C:\Users\Olivia\wealth-machine`.
- TESTED: screenshot command execution works on the live Windows desktop.
- TESTED: shell command execution works through the bridge.
- TESTED: `output.json` updates.
- TESTED: `.openclaw_bridge_state.json` updates.
- TESTED: `last_frame.png` updates.
- TESTED: `ops\bridge_smoke_test.py` passed end-to-end on the live desktop.
- LIVE: `ops\browser_helper.py probe` is the preferred browser helper path.
- PARTIAL: browser-specific built-ins inside `portable_agent.py`.
- PARTIAL: direct Codex self-operation.
- FAILED: built-in `browser_probe` dispatch was observed falling through to raw shell.

## Resume Checklist

Window: Codex Terminal

```powershell
Set-Location C:\Users\Olivia\wealth-machine
git status --short
```

Window: Controller PowerShell

```powershell
Set-Location C:\Users\Olivia\wealth-machine
Get-Content .\commands.json -Raw
python .\ops\bridge_result_check.py
```

Window: Bridge PowerShell

```powershell
Set-Location C:\Users\Olivia\wealth-machine
$token = (Get-Content C:\OpenClawBridge\.github_token -Raw).Trim()
python .\portable_agent.py "$token"
```

Window: Desktop PowerShell

```powershell
Set-Location C:\Users\Olivia\wealth-machine
python .\ops\bridge_smoke_test.py
```

Continue only after the smoke test passes.

## Checkpoint Procedure

Window: Controller PowerShell

```powershell
$src="C:\Users\Olivia\wealth-machine"
$stamp=Get-Date -Format "yyyyMMdd-HHmmss"
$dst="C:\Users\Olivia\LittleHomie-checkpoints\bridge-$stamp"
New-Item -ItemType Directory -Force -Path $dst | Out-Null
Set-Location $src
git status --short | Set-Content "$dst\git-status.txt"
git diff -- . ':(exclude).env' ':(exclude)VAULT/**' | Set-Content "$dst\workspace.diff"
$files=@("LITTLE_HOMIE.md","portable_agent.py","commands.json","output.json",".openclaw_bridge_state.json","last_frame.png","ops\bridge_smoke_test.py","ops\bridge_send_command.py","ops\bridge_result_check.py","ops\browser_helper.py","ops\BRIDGE_V2.md","ops\LITTLE_HOMIE_RULES.md","ops\SESSION_STATE.md","ops\RESTORE_HANDOFF.md","ops\MISTAKE_LEDGER.md")
foreach($f in $files){if(Test-Path $f){$to=Join-Path $dst $f; New-Item -ItemType Directory -Force -Path (Split-Path $to) | Out-Null; Copy-Item $f $to -Force}}
Write-Host "Checkpoint saved to $dst"
```

## Handoff Template

Copy this into the next session:

```text
Little Homie resume:
- Read ops/LITTLE_HOMIE_RULES.md first.
- Read ops/SESSION_STATE.md second.
- Read ops/BRIDGE_V2.md third.
- Read ops/MISTAKE_LEDGER.md before retrying failures.
- Proven: screenshot, shell, output.json, state, last_frame, smoke test.
- Use ops/browser_helper.py probe through the shell path for browser/window state.
- Use ops/bridge_result_check.py before interpreting output.json.
- Do not rely on built-in browser_probe dispatch unless newly proven.
- Keep instructions short, one-step, and labeled by exact window.
```
