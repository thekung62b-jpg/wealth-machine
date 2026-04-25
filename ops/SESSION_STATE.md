# Session State

Purpose: quick continuity snapshot for the next Little Homie session.

## Current Working State

- TESTED: bridge smoke test passed on live Windows desktop for screenshot -> shell -> output/state/frame.
- LIVE: use shell-command bridge path for safe control.
- LIVE: use `ops\bridge_result_check.py` before interpreting `output.json`.
- LIVE: use `ops\browser_helper.py probe` for browser/window metadata through the shell path.
- PARTIAL: browser navigation/control beyond opening a page and probing foreground state.
- PARTIAL: direct Codex self-operation.
- FAILED: built-in `browser_probe` dispatch path; do not debug it again without a fresh reason.

## Current Queue/Result Note

- `commands.json` currently contains a queued `python .\ops\browser_helper.py probe` command.
- `output.json` currently shows an older failed `browser_probe` raw-shell result.
- `ops\bridge_result_check.py` correctly labels this as `STALE`.

## Single Best Next Move

Window: Bridge PowerShell

```powershell
Set-Location C:\Users\Olivia\wealth-machine
$token = (Get-Content C:\OpenClawBridge\.github_token -Raw).Trim()
python .\portable_agent.py "$token"
```

Then:

Window: Controller PowerShell

```powershell
Set-Location C:\Users\Olivia\wealth-machine
python .\ops\bridge_result_check.py
```

Continue only if it prints `MATCH`.
