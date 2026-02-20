#!/usr/bin/env python3
import base64
import json
import os
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from urllib.request import Request, urlopen

REPO = os.getenv("WM_REPO", "thekung62b-jpg/wealth-machine")
POLL_SECONDS = float(os.getenv("WM_POLL_SECONDS", "3"))
STATE_PATH = os.path.expanduser("~/.openclaw_bridge_state.json")


def gh_get_json(token, path):
    req = Request(f"https://api.github.com/repos/{REPO}/contents/{path}")
    req.add_header("Authorization", f"token {token}")
    req.add_header("Accept", "application/vnd.github+json")
    with urlopen(req, timeout=20) as r:
        data = json.loads(r.read().decode())
    content = base64.b64decode(data["content"]).decode()
    return json.loads(content), data.get("sha", "")


def gh_put_json(token, path, payload, message):
    # fetch current sha if file exists
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
    with urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def load_state():
    if os.path.exists(STATE_PATH):
        try:
            with open(STATE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"last_id": ""}


def save_state(state):
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def run_command(cmd):
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return {
        "exitCode": p.returncode,
        "stdout": (p.stdout or "")[-8000:],
        "stderr": (p.stderr or "")[-8000:],
    }


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def main(token):
    state = load_state()
    hostname = socket.gethostname()
    print(f"📡 Portable Agent: LISTENING on {hostname} (repo={REPO})")

    while True:
        try:
            cmd_data, _ = gh_get_json(token, "commands.json")
            cmd_id = cmd_data.get("id", "")
            cmd = cmd_data.get("cmd", "")

            if cmd_id and cmd_id != state.get("last_id") and cmd:
                print(f"📥 EXECUTE[{cmd_id}]: {cmd}")
                started = now_iso()
                result = run_command(cmd)
                finished = now_iso()

                output = {
                    "id": cmd_id,
                    "cmd": cmd,
                    "host": hostname,
                    "startedAt": started,
                    "finishedAt": finished,
                    **result,
                }

                gh_put_json(
                    token,
                    "output.json",
                    output,
                    f"bridge: result {cmd_id}",
                )

                state["last_id"] = cmd_id
                state["last_finished_at"] = finished
                save_state(state)
                print(f"✅ DONE[{cmd_id}] exit={result['exitCode']}")

        except Exception as e:
            print(f"⚠️ bridge error: {e}")

        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        print("Usage: python portable_agent.py <github_token>")
