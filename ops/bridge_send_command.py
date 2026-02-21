#!/usr/bin/env python3
import argparse
import json
import uuid
from pathlib import Path


def load(path: Path):
    if not path.exists():
        return {"commands": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"commands": []}

    # normalize old single-command format to queue format
    if isinstance(data, dict) and "commands" in data and isinstance(data["commands"], list):
        return data
    if isinstance(data, dict) and data.get("id") and data.get("cmd"):
        return {"commands": [data]}
    return {"commands": []}


def main():
    p = argparse.ArgumentParser(description="Queue a bridge command into commands.json")
    p.add_argument("cmd", help="Shell command to run on bridged computer")
    p.add_argument("--id", dest="cmd_id", default=None, help="Optional command id")
    p.add_argument("--path", default="commands.json", help="Path to commands.json")
    p.add_argument("--os", dest="os_tag", default="", help="Optional target OS: windows|linux|macos")
    p.add_argument("--host", dest="host", default="", help="Optional target hostname")
    p.add_argument("--cwd", dest="cwd", default="", help="Optional working directory")
    p.add_argument("--replace", action="store_true", help="Replace queue with this single command")
    args = p.parse_args()

    cmd_obj = {
        "id": args.cmd_id or f"cmd_{uuid.uuid4().hex[:10]}",
        "cmd": args.cmd,
    }
    if args.os_tag:
        cmd_obj["os"] = args.os_tag.lower()
    if args.host:
        cmd_obj["host"] = args.host
    if args.cwd:
        cmd_obj["cwd"] = args.cwd

    out = Path(args.path)
    payload = {"commands": [cmd_obj]} if args.replace else load(out)
    if not args.replace:
        payload.setdefault("commands", []).append(cmd_obj)

    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Queued {cmd_obj['id']} in {out}")


if __name__ == "__main__":
    main()
