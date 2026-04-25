#!/usr/bin/env python3
"""
Read-only bridge result checker.

Compares the latest queued command id in commands.json with output.json so stale
results are labeled before anyone interprets stdout/stderr.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COMMANDS = ROOT / "commands.json"
DEFAULT_OUTPUT = ROOT / "output.json"


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as exc:
        return {"_error": f"{path.name} invalid JSON: {exc}"}

    if not isinstance(data, dict):
        return {"_error": f"{path.name} is not a JSON object"}
    return data


def queued_ids(payload: dict[str, Any]) -> list[str]:
    commands = payload.get("commands")
    if isinstance(commands, list):
        ids: list[str] = []
        for command in commands:
            if isinstance(command, dict) and command.get("id"):
                ids.append(str(command["id"]))
        return ids

    if payload.get("id"):
        return [str(payload["id"])]

    return []


def main() -> int:
    parser = argparse.ArgumentParser(description="Check whether output.json matches the latest queued bridge command.")
    parser.add_argument("--commands", default=str(DEFAULT_COMMANDS), help="Path to commands.json")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Path to output.json")
    args = parser.parse_args()

    commands_path = Path(args.commands)
    output_path = Path(args.output)
    commands_payload = read_json(commands_path)
    output_payload = read_json(output_path)

    for payload in (commands_payload, output_payload):
        if payload.get("_error"):
            print(f"FAILED: {payload['_error']}")
            return 2

    ids = queued_ids(commands_payload)
    latest_id = ids[-1] if ids else ""
    output_id = str(output_payload.get("id", ""))

    if not latest_id:
        print("MISSING: commands.json has no queued command id")
        return 2

    if not output_id:
        print(f"MISSING: output.json has no result id; latest queued id is {latest_id}")
        return 2

    if output_id != latest_id:
        print(f"STALE: latest queued id is {latest_id}, but output.json id is {output_id}")
        print(json.dumps(output_payload, indent=2))
        return 1

    print(f"MATCH: output.json matches latest queued id {latest_id}")
    print(json.dumps(output_payload, indent=2))
    return 0 if output_payload.get("status") == "done" else 1


if __name__ == "__main__":
    sys.exit(main())
