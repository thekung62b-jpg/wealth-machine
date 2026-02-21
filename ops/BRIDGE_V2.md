# Bridge V2 (GitHub Command Bridge)

## What improved

1. **Queue support**
- `commands.json` can now be either:
  - single command object (`{id, cmd}`), or
  - command queue (`{ "commands": [ ... ] }`)

2. **Dedupe + persistence**
- Agent stores executed IDs in `~/.openclaw_bridge_state.json`.
- Prevents duplicate execution after restarts.

3. **Targeting**
- Optional per-command targeting:
  - `os`: `windows|linux|macos`
  - `host`: specific hostname
  - `cwd`: working directory

4. **Stability**
- Poll jitter to avoid collisions.
- Command timeout (`WM_CMD_TIMEOUT`, default 90s).
- Larger stdout/stderr capture and structured `output.json`.

## New helper usage

Queue command:
```bash
python ops/bridge_send_command.py "start calc.exe" --os windows
```

Replace queue with one command:
```bash
python ops/bridge_send_command.py "start https://www.youtube.com" --os windows --replace
```

Target specific host:
```bash
python ops/bridge_send_command.py "start calc.exe" --host DESKTOP-CA6S7AM
```

## Agent run (Windows)

```powershell
$token = (Get-Content C:\OpenClawBridge\.github_token -Raw).Trim()
python C:\OpenClawBridge\wealth-machine\portable_agent.py "$token"
```

## Recommended pattern

- Keep one bridge terminal always running.
- Queue commands from controller side.
- Read execution result from `output.json`.
- Rotate token if exposed.
