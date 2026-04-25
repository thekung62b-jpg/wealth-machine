#!/usr/bin/env python3
"""
Local browser/app helper for the proven shell-command bridge path.

Action: probe
- reads the current foreground window title/process
- saves a fresh screenshot to last_frame.png
- prints compact JSON to stdout for portable_agent.py to capture in output.json

Action: active-window
- reads the current foreground window title/process

Action: notepad-safe-type-test
- types the TEST 5 text only after foreground Notepad verification

No network, clicks, or browser automation.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pyautogui
import psutil
from PIL import ImageGrab


ROOT = Path(__file__).resolve().parents[1]
LAST_FRAME_FILE = ROOT / "last_frame.png"
TEST5_TEXT = "LITTLE HOMIE CONTROL TEST PASS"


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


def enum_windows_for_pid(process_id: int) -> list[int]:
    if os.name != "nt":
        raise RuntimeError("window enumeration is Windows-only")

    user32 = ctypes.windll.user32
    windows: list[int] = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def enum_proc(hwnd: int, _lparam: int) -> bool:
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if int(pid.value) == process_id and user32.IsWindowVisible(hwnd):
            windows.append(int(hwnd))
        return True

    user32.EnumWindows(enum_proc, 0)
    return windows


def activate_window(hwnd: int) -> None:
    user32 = ctypes.windll.user32
    user32.ShowWindow(ctypes.c_void_p(hwnd), 5)
    user32.SetForegroundWindow(ctypes.c_void_p(hwnd))


def click_inside_window(hwnd: int) -> dict[str, int]:
    class RECT(ctypes.Structure):
        _fields_ = [
            ("left", ctypes.c_long),
            ("top", ctypes.c_long),
            ("right", ctypes.c_long),
            ("bottom", ctypes.c_long),
        ]

    user32 = ctypes.windll.user32
    rect = RECT()
    if not user32.GetWindowRect(ctypes.c_void_p(hwnd), ctypes.byref(rect)):
        raise RuntimeError("failed to read Notepad window bounds")

    width = rect.right - rect.left
    height = rect.bottom - rect.top
    x = rect.left + min(120, max(10, width - 10))
    y = rect.top + min(120, max(10, height - 10))
    pyautogui.click(x, y)
    return {"x": x, "y": y}


def is_notepad_foreground(foreground: dict[str, Any]) -> bool:
    process_name = str(foreground.get("process_name", "")).lower()
    title = str(foreground.get("title", "")).lower()
    return process_name == "notepad.exe" or "notepad" in title


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


def notepad_safe_type_test() -> dict[str, Any]:
    proc = subprocess.Popen(["notepad.exe"])
    hwnd = 0
    focus_click: dict[str, int] = {}
    for _ in range(40):
        windows = enum_windows_for_pid(proc.pid)
        if windows:
            hwnd = windows[0]
            activate_window(hwnd)
            focus_click = click_inside_window(hwnd)
            break
        time.sleep(0.2)

    time.sleep(0.3)
    foreground = foreground_window()
    if not is_notepad_foreground(foreground):
        screenshot = take_screenshot()
        return {
            "ok": False,
            "action": "notepad-safe-type-test",
            "typed": False,
            "reason": "foreground window is not Notepad",
            "foreground": foreground,
            "focus_click": focus_click,
            "screenshot": screenshot,
        }

    pyautogui.write(TEST5_TEXT, interval=0.03)
    time.sleep(0.5)
    screenshot = take_screenshot()
    return {
        "ok": True,
        "action": "notepad-safe-type-test",
        "typed": True,
        "typed_text": TEST5_TEXT,
        "foreground_before_typing": foreground,
        "focus_click": focus_click,
        "screenshot": screenshot,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Safe local browser helper")
    parser.add_argument(
        "action",
        choices=["probe", "active-window", "notepad-safe-type-test"],
        help="Supported actions: probe, active-window, notepad-safe-type-test",
    )
    args = parser.parse_args()

    try:
        if args.action == "probe":
            print(json.dumps(probe(), separators=(",", ":")))
            return 0
        if args.action == "active-window":
            print(json.dumps(active_window(), separators=(",", ":")))
            return 0
        if args.action == "notepad-safe-type-test":
            print(json.dumps(notepad_safe_type_test(), separators=(",", ":")))
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
