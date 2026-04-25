#!/usr/bin/env python3
"""
One-action local browser helper for the proven shell-command bridge path.

Action: probe
- reads the current foreground window title/process
- saves a fresh screenshot to last_frame.png
- prints compact JSON to stdout for portable_agent.py to capture in output.json

Action: active-window
- reads the current foreground window title/process

No network, clicks, typing, or browser automation.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psutil
from PIL import ImageGrab


ROOT = Path(__file__).resolve().parents[1]
LAST_FRAME_FILE = ROOT / "last_frame.png"


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def foreground_window() -> dict[str, Any]:
    if os.name != "nt":
        raise RuntimeError("foreground window probing is Windows-only")

    user32 = ctypes.windll.user32
    user32.GetForegroundWindow.restype = ctypes.c_void_p
    user32.GetWindowThreadProcessId.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_ulong),
    ]
    user32.GetWindowTextLengthW.argtypes = [ctypes.c_void_p]
    user32.GetWindowTextW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]

    hwnd = user32.GetForegroundWindow()
    pid = ctypes.c_ulong()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

    title_len = user32.GetWindowTextLengthW(hwnd)
    title_buf = ctypes.create_unicode_buffer(max(title_len + 1, 512))
    user32.GetWindowTextW(hwnd, title_buf, len(title_buf))

    process_id = int(pid.value)
    process_name = ""
    process_exe = ""
    if process_id:
        try:
            proc = psutil.Process(process_id)
            process_name = proc.name()
            process_exe = proc.exe()
        except psutil.Error:
            pass

    return {
        "hwnd": int(hwnd or 0),
        "process_id": process_id,
        "process_name": process_name,
        "process_exe": process_exe,
        "title": title_buf.value,
    }


def take_screenshot() -> dict[str, Any]:
    image = ImageGrab.grab()
    image.save(LAST_FRAME_FILE)
    stat = LAST_FRAME_FILE.stat()
    return {
        "path": str(LAST_FRAME_FILE),
        "width": image.width,
        "height": image.height,
        "bytes": stat.st_size,
        "sha256": file_sha256(LAST_FRAME_FILE),
    }


def probe() -> dict[str, Any]:
    foreground = foreground_window()
    screenshot = take_screenshot()
    return {
        "ok": True,
        "action": "probe",
        "host": os.getenv("COMPUTERNAME") or platform.node(),
        "timestamp": iso_now(),
        "foreground": foreground,
        "screenshot": screenshot,
    }


def active_window() -> dict[str, Any]:
    return {
        "ok": True,
        "action": "active-window",
        "host": os.getenv("COMPUTERNAME") or platform.node(),
        "timestamp": iso_now(),
        "foreground": foreground_window(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Safe local browser helper")
    parser.add_argument(
        "action",
        choices=["probe", "active-window"],
        help="Supported actions: probe, active-window",
    )
    args = parser.parse_args()

    try:
        if args.action == "probe":
            print(json.dumps(probe(), separators=(",", ":")))
            return 0
        if args.action == "active-window":
            print(json.dumps(active_window(), separators=(",", ":")))
            return 0
    except Exception as exc:
        payload = {
            "ok": False,
            "action": args.action,
            "host": os.getenv("COMPUTERNAME") or platform.node(),
            "timestamp": iso_now(),
            "error": str(exc),
        }
        print(json.dumps(payload, separators=(",", ":")), file=sys.stderr)
        return 1

    return 2


if __name__ == "__main__":
    sys.exit(main())
