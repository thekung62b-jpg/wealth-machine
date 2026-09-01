# Bridge return-path repair + diagnostics (LH-BROWSER-WEB-SEARCH-001)
#
# Purpose: the inbound bridge channel works (the agent polls commands.json),
# but no result comes back. The agent's post-command push is a single && chain:
#
#   git add . && git commit -m "Result <id>" && git pull origin master --no-rebase && git push ...
#
# On a stale or dirty checkout the `git pull` conflicts, the chain breaks, and
# the result is never pushed. This script repairs ONLY that: it puts the local
# checkout cleanly onto origin/master so the agent's own push chain succeeds.
#
# Handles no credentials. Installs nothing. Everything it learns goes to stdout,
# which the agent captures into output.json and pushes for us.

$ErrorActionPreference = "Continue"
Set-Location "C:\Users\Olivia\wealth-machine"

function Section($name, $block) {
    Write-Output ""
    Write-Output "===== $name ====="
    try   { & $block 2>&1 | Out-String | ForEach-Object { $_.TrimEnd() } }
    catch { Write-Output "ERROR: $($_.Exception.Message)" }
}

Write-Output "BRIDGE_DIAG_02"
Write-Output "utc=$([DateTime]::UtcNow.ToString('o'))"
Write-Output "host=$env:COMPUTERNAME"
Write-Output "user=$env:USERNAME"
Write-Output "cwd=$((Get-Location).Path)"

Section "git-state-before" { git log --oneline -3; git status --porcelain }

# --- the repair: land the checkout cleanly on origin/master ---
# stash (not discard) any local edits so nothing is lost and the merge is clean.
Section "repair" {
    git stash push -u -m "bridge-repair-autostash"
    git fetch origin master
    git merge --no-edit origin/master
}

Section "git-state-after" { git log --oneline -3; git status --porcelain }

# --- read-only environment probe for the next milestone step ---
Section "wsl"    { wsl.exe -l -v }
Section "docker" { docker version }
Section "winget" { winget --version }

Write-Output ""
Write-Output "BRIDGE_REPAIR_DONE host=$env:COMPUTERNAME"
