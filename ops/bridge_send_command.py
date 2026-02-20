#!/usr/bin/env python3
import argparse
import json
import uuid
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description="Write a new bridge command into commands.json")
    p.add_argument("cmd", help="Shell command to run on bridged computer")
    p.add_argument("--id", dest="cmd_id", default=None, help="Optional command id")
    p.add_argument("--path", default="commands.json", help="Path to commands.json")
    args = p.parse_args()

    payload = {
        "id": args.cmd_id or f"cmd_{uuid.uuid4().hex[:10]}",
        "cmd": args.cmd,
    }

    out = Path(args.path)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {out} with id={payload['id']}")


if __name__ == "__main__":
    main()
