#!/usr/bin/env python3
"""
Local closed-loop smoke test for the Windows bridge artifacts.

Safe by design:
- no GitHub token
- no network
- no click/type actions
- only captures a screenshot and runs a fixed echo command
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from PIL import ImageGrab
except Exception as exc:  # pragma: no cover - exercised only on missing/broken PIL installs.
    ImageGrab = None
    IMAGEGRAB_IMPORT_ERROR = exc
else:
    IMAGEGRAB_IMPORT_ERROR = None


ROOT = Path(__file__).resolve().parents[1]
COMMANDS_FILE = ROOT / "commands.json"
OUTPUT_FILE = ROOT / "output.json"
STATE_FILE = ROOT / ".openclaw_bridge_state.json"
LAST_FRAME_FILE = ROOT / "last_frame.png"
HOST = os.getenv("COMPUTERNAME") or platform.node()


class SmokeFailure(Exception):
    pass


@dataclass(frozen=True)
class FileSnapshot:
    exists: bool
    size: int
    mtime_ns: int
    sha256: str


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(status: str, message: str) -> None:
    print(f"[{iso_now()}] {status:<4} {message}", flush=True)


def snapshot(path: Path) -> FileSnapshot:
    if not path.exists():
        return FileSnapshot(False, 0, 0, "")

    data = path.read_bytes()
    stat = path.stat()
    return FileSnapshot(
        True,
        stat.st_size,
        stat.st_mtime_ns,
        hashlib.sha256(data).hexdigest(),
    )


def backup_file(path: Path) -> bytes | None:
    return path.read_bytes() if path.exists() else None


def restore_file(path: Path, content: bytes | None) -> None:
    if content is None:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        return

    path.write_bytes(content)


def changed(before: FileSnapshot, after: FileSnapshot) -> bool:
    return before != after


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as exc:
        raise SmokeFailure(f"{path.name} is not valid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise SmokeFailure(f"{path.name} must contain a JSON object")
    return data


def load_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return {"executed_ids": []}

    state = read_json(STATE_FILE)
    ids = state.get("executed_ids", [])
    if not isinstance(ids, list):
        raise SmokeFailure("state executed_ids must be a list")
    return state


def executed_ids(state: dict[str, Any]) -> set[str]:
    return {str(item) for item in state.get("executed_ids", [])}


def save_state(state: dict[str, Any], ids: set[str]) -> None:
    state["executed_ids"] = sorted(ids)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def write_output(
    cmd_id: str,
    status: str,
    started_at: str,
    *,
    result: str = "",
    stdout: str = "",
    stderr: str = "",
    exit_code: int | None = None,
    artifact: str = "",
) -> None:
    payload: dict[str, Any] = {
        "id": cmd_id,
        "status": status,
        "host": HOST,
        "started_at": started_at,
        "finished_at": iso_now(),
        "result": result,
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": exit_code,
    }
    if artifact:
        payload["artifact"] = artifact

    OUTPUT_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_smoke_queue(shot_id: str, shell_id: str, marker: str) -> str | None:
    original = COMMANDS_FILE.read_text(encoding="utf-8") if COMMANDS_FILE.exists() else None
    payload = {
        "commands": [
            {
                "id": shot_id,
                "cmd": "screenshot",
                "host": HOST,
                "os": "windows",
            },
            {
                "id": shell_id,
                "cmd": f"echo {marker}",
                "host": HOST,
                "os": "windows",
            },
        ]
    }
    COMMANDS_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return original


def restore_commands(original: str | None) -> None:
    if original is None:
        try:
            COMMANDS_FILE.unlink()
        except FileNotFoundError:
            pass
        return

    COMMANDS_FILE.write_text(original, encoding="utf-8")


def load_commands() -> list[dict[str, Any]]:
    payload = read_json(COMMANDS_FILE)
    commands = payload.get("commands")
    if isinstance(commands, list):
        return [item for item in commands if isinstance(item, dict)]

    if payload.get("id") and payload.get("cmd"):
        return [payload]

    return []


def command_applies(command: dict[str, Any]) -> bool:
    target_host = command.get("host")
    if target_host and target_host != HOST:
        return False

    target_os = command.get("os")
    if target_os and str(target_os).lower() != "windows":
        return False

    return True


def run_command(command: dict[str, Any], state: dict[str, Any], timeout: int) -> None:
    cmd_id = str(command.get("id", ""))
    action = str(command.get("cmd", ""))
    if not cmd_id or not action:
        raise SmokeFailure("smoke command is missing id or cmd")

    ids = executed_ids(state)
    if cmd_id in ids:
        raise SmokeFailure(f"smoke command id was already executed: {cmd_id}")

    started_at = iso_now()
    try:
        if action == "screenshot":
            if ImageGrab is None:
                raise SmokeFailure(f"PIL ImageGrab is unavailable: {IMAGEGRAB_IMPORT_ERROR}")
            ImageGrab.grab().save(LAST_FRAME_FILE)
            write_output(
                cmd_id,
                "done",
                started_at,
                result="SCREENSHOT_SAVED",
                artifact=str(LAST_FRAME_FILE),
            )
            return

        proc = subprocess.run(
            action,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        result = proc.stdout if proc.stdout else proc.stderr
        status = "done" if proc.returncode == 0 else "failed"
        write_output(
            cmd_id,
            status,
            started_at,
            result=result,
            stdout=proc.stdout,
            stderr=proc.stderr,
            exit_code=proc.returncode,
        )
        if proc.returncode != 0:
            raise SmokeFailure(f"shell command failed with exit code {proc.returncode}")
    except subprocess.TimeoutExpired as exc:
        stderr = f"command timed out after {timeout}s"
        write_output(cmd_id, "failed", started_at, stderr=stderr, exit_code=None)
        raise SmokeFailure(stderr) from exc
    except Exception as exc:
        if not OUTPUT_FILE.exists() or read_json(OUTPUT_FILE).get("id") != cmd_id:
            write_output(cmd_id, "failed", started_at, result=str(exc), stderr=str(exc))
        if isinstance(exc, SmokeFailure):
            raise
        raise SmokeFailure(f"{action} command failed: {exc}") from exc
    finally:
        ids = executed_ids(state)
        ids.add(cmd_id)
        save_state(state, ids)


def check(condition: bool, message: str, failures: list[str]) -> None:
    if condition:
        log("PASS", message)
        return

    failures.append(message)
    log("FAIL", message)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prove screenshot -> shell -> output/state/frame bridge artifacts update locally."
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=15,
        help="Timeout in seconds for the shell command.",
    )
    args = parser.parse_args()

    if platform.system().lower() != "windows":
        log("FAIL", "this smoke test is intended for the Windows bridge host")
        return 1

    failures: list[str] = []
    run_id = uuid.uuid4().hex[:10]
    shot_id = f"cmd_smoke_shot_{run_id}"
    shell_id = f"cmd_smoke_shell_{run_id}"
    marker = f"BRIDGE_SMOKE_{run_id}"
    original_commands: str | None = None

    log("INFO", "starting local bridge smoke test; no token or network is used")

    output_backup = backup_file(OUTPUT_FILE)
    state_backup = backup_file(STATE_FILE)
    frame_backup = backup_file(LAST_FRAME_FILE)
    frame_before = snapshot(LAST_FRAME_FILE)
    output_before = snapshot(OUTPUT_FILE)
    state_before = snapshot(STATE_FILE)

    try:
        original_commands = write_smoke_queue(shot_id, shell_id, marker)
        log("PASS", "wrote temporary screenshot -> shell command queue")

        commands = [command for command in load_commands() if command_applies(command)]
        check(len(commands) == 2, "loaded two applicable smoke commands", failures)
        if len(commands) != 2:
            raise SmokeFailure("could not load the expected two smoke commands")

        state = load_state()
        run_command(commands[0], state, args.timeout)

        frame_after_shot = snapshot(LAST_FRAME_FILE)
        output_after_shot = snapshot(OUTPUT_FILE)
        state_after_shot = snapshot(STATE_FILE)
        shot_output = read_json(OUTPUT_FILE)
        shot_state = load_state()

        check(changed(frame_before, frame_after_shot), "last_frame.png changed after screenshot", failures)
        check(frame_after_shot.exists and frame_after_shot.size > 0, "last_frame.png exists and is non-empty", failures)
        check(changed(output_before, output_after_shot), "output.json changed after screenshot", failures)
        check(shot_output.get("id") == shot_id, "output.json recorded screenshot command id", failures)
        check(shot_output.get("status") == "done", "screenshot command status is done", failures)
        check(shot_output.get("result") == "SCREENSHOT_SAVED", "screenshot result is SCREENSHOT_SAVED", failures)
        check(changed(state_before, state_after_shot), "bridge state changed after screenshot", failures)
        check(shot_id in executed_ids(shot_state), "bridge state contains screenshot command id", failures)

        run_command(commands[1], shot_state, args.timeout)

        output_after_shell = snapshot(OUTPUT_FILE)
        state_after_shell = snapshot(STATE_FILE)
        shell_output = read_json(OUTPUT_FILE)
        shell_state = load_state()

        check(changed(output_after_shot, output_after_shell), "output.json changed after shell command", failures)
        check(shell_output.get("id") == shell_id, "output.json recorded shell command id", failures)
        check(shell_output.get("status") == "done", "shell command status is done", failures)
        check(shell_output.get("exit_code") == 0, "shell command exit code is 0", failures)
        check(marker in str(shell_output.get("stdout", "")), "shell stdout contains smoke marker", failures)
        check(changed(state_after_shot, state_after_shell), "bridge state changed after shell command", failures)
        check(shell_id in executed_ids(shell_state), "bridge state contains shell command id", failures)

    except Exception as exc:
        failures.append(str(exc))
        log("FAIL", str(exc))
    finally:
        try:
            restore_commands(original_commands)
            log("PASS", "commands.json restored")
        except Exception as exc:
            failures.append(f"failed to restore commands.json: {exc}")
            log("FAIL", f"failed to restore commands.json: {exc}")

        if failures:
            try:
                restore_file(OUTPUT_FILE, output_backup)
                restore_file(STATE_FILE, state_backup)
                restore_file(LAST_FRAME_FILE, frame_backup)
                log("PASS", "restored output/state/frame after failed smoke run")
            except Exception as exc:
                failures.append(f"failed to restore smoke artifacts: {exc}")
                log("FAIL", f"failed to restore smoke artifacts: {exc}")

    if failures:
        log("FAIL", f"bridge smoke test failed with {len(failures)} failure(s)")
        return 1

    log("PASS", "bridge smoke test passed: screenshot -> shell -> output/state/frame changed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
