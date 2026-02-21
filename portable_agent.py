#!/usr/bin/env python3
import base64
import json
import os
import platform
import random
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from urllib.request import Request, urlopen

REPO = os.getenv("WM_REPO", "thekung62b-jpg/wealth-machine")
POLL_SECONDS = float(os.getenv("WM_POLL_SECONDS", "3"))
CMD_TIMEOUT = int(os.getenv("WM_CMD_TIMEOUT", "90"))
STATE_PATH = os.path.expanduser("~/.openclaw_bridge_state.json")
HISTORY_LIMIT = 300


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def detect_os_tag():
    s = platform.system().lower()
    if "windows" in s:
        return "windows"
    if "linux" in s:
        return "linux"
    if "darwin" in s or "mac" in s:
        return "macos"
    return s


def gh_get_json(token, path):
    req = Request(f"https://api.github.com/repos/{REPO}/contents/{path}")
    req.add_header("Authorization", f"token {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "portable-agent")
    with urlopen(req, timeout=20) as r:
        data = json.loads(r.read().decode())
    content = base64.b64decode(data["content"]).decode()
    return json.loads(content), data.get("sha", "")


def gh_put_json(token, path, payload, message):
    sha = None
    try:
        _, sha = gh_get_json(token, path)
    except Exception:
        sha = None

    body = {
        "message": message,
        "content": base64.b64encode(json.dumps(payload, ensure_ascii=False, indent=2).encode()).decode(),
        "branch": "master",
    }
    if sha:
        body["sha"] = sha

    req = Request(
        f"https://api.github.com/repos/{REPO}/contents/{path}",
        data=json.dumps(body).encode(),
        method="PUT",
    )
    req.add_header("Authorization", f"token {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "portable-agent")
    with urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def load_state():
    if os.path.exists(STATE_PATH):
        try:
            with open(STATE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                data.setdefault("executed_ids", [])
                return data
        except Exception:
            pass
    return {"last_id": "", "executed_ids": []}


def save_state(state):
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def normalize_commands(raw):
    """
    Supported shapes:
      {"id":"x","cmd":"..."}
      {"commands":[{"id":"x","cmd":"..."}, ...]}
    """
    if isinstance(raw, dict) and isinstance(raw.get("commands"), list):
        return [c for c in raw["commands"] if isinstance(c, dict)]
    if isinstance(raw, dict) and raw.get("id") and raw.get("cmd"):
        return [raw]
    return []


def is_command_for_this_host(cmd_obj, os_tag):
    target_os = str(cmd_obj.get("os", "")).strip().lower()
    if target_os and target_os != os_tag:
        return False
    target_host = str(cmd_obj.get("host", "")).strip().lower()
    if target_host and target_host not in {socket.gethostname().lower(), "*", "any"}:
        return False
    return True


def pick_next_command(commands, state, os_tag):
    done = set(state.get("executed_ids", []))
    for c in commands:
        cid = str(c.get("id", "")).strip()
        if not cid or cid in done:
            continue
        if not is_command_for_this_host(c, os_tag):
            continue
        if not str(c.get("cmd", "")).strip():
            continue
        return c
    return None


def run_command(cmd_obj):
    cmd = cmd_obj["cmd"]
    cwd = cmd_obj.get("cwd") or None
    shell_flag = bool(cmd_obj.get("shell", True))
    p = subprocess.run(
        cmd,
        shell=shell_flag,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=CMD_TIMEOUT,
    )
    return {
        "exitCode": p.returncode,
        "stdout": (p.stdout or "")[-12000:],
        "stderr": (p.stderr or "")[-12000:],
    }


def trim_history(state):
    ids = state.get("executed_ids", [])
    if len(ids) > HISTORY_LIMIT:
        state["executed_ids"] = ids[-HISTORY_LIMIT:]


def main(token):
    state = load_state()
    hostname = socket.gethostname()
    os_tag = detect_os_tag()
    print(f"📡 Portable Agent: LISTENING on {hostname} ({os_tag}) repo={REPO}")

    while True:
        try:
            raw, _ = gh_get_json(token, "commands.json")
            commands = normalize_commands(raw)
            next_cmd = pick_next_command(commands, state, os_tag)

            if next_cmd:
                cid = next_cmd["id"]
                cmd = next_cmd["cmd"]
                print(f"📥 EXECUTE[{cid}]: {cmd}")

                started = now_iso()
                try:
                    result = run_command(next_cmd)
                except subprocess.TimeoutExpired as te:
                    result = {
                        "exitCode": 124,
                        "stdout": (te.stdout or "")[-12000:] if te.stdout else "",
                        "stderr": f"Command timed out after {CMD_TIMEOUT}s",
                    }
                finished = now_iso()

                output = {
                    "id": cid,
                    "cmd": cmd,
                    "host": hostname,
                    "os": os_tag,
                    "startedAt": started,
                    "finishedAt": finished,
                    **result,
                }

                gh_put_json(token, "output.json", output, f"bridge: result {cid}")

                state["last_id"] = cid
                state["last_finished_at"] = finished
                state.setdefault("executed_ids", []).append(cid)
                trim_history(state)
                save_state(state)
                print(f"✅ DONE[{cid}] exit={result['exitCode']}")

        except Exception as e:
            print(f"⚠️ bridge error: {e}")

        # jitter prevents lockstep collisions if multiple agents poll
        sleep_s = POLL_SECONDS + random.uniform(0, 0.6)
        time.sleep(sleep_s)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        print("Usage: python portable_agent.py <github_token>")
