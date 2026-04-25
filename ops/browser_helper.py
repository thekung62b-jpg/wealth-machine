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
- sets and reads the TEST 5 text in a UIA-discovered Notepad edit control

No network, clicks, keystrokes, or browser automation.
"""

from __future__ import annotations

import argparse
import base64
import ctypes
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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


def run_powershell_json(script: str) -> dict[str, Any]:
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    proc = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-EncodedCommand",
            encoded,
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    json_line = next((line for line in reversed(lines) if line.startswith("{")), "")
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "PowerShell UIA command failed")
    if not json_line:
        raise RuntimeError("PowerShell UIA command returned no JSON")

    payload = json.loads(json_line)
    if not isinstance(payload, dict):
        raise RuntimeError("PowerShell UIA command returned non-object JSON")
    if proc.stderr.strip():
        payload["stderr"] = proc.stderr.strip()
    return payload


def send_window_message(hwnd: int, message: int, wparam: int, lparam: Any) -> int:
    user32 = ctypes.windll.user32
    user32.SendMessageW.argtypes = None
    user32.SendMessageW.restype = ctypes.c_ssize_t
    return int(user32.SendMessageW(ctypes.c_void_p(hwnd), message, wparam, lparam))


def set_window_text(hwnd: int, text: str) -> int:
    return send_window_message(hwnd, 0x000C, 0, ctypes.c_wchar_p(text))


def get_window_text(hwnd: int) -> str:
    length = send_window_message(hwnd, 0x000E, 0, 0)
    buffer = ctypes.create_unicode_buffer(max(length + 1, len(TEST5_TEXT) + 1))
    send_window_message(hwnd, 0x000D, len(buffer), buffer)
    return buffer.value


def notepad_uia_script() -> str:
    return """
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$proc = Start-Process notepad.exe -PassThru
$window = $null
for ($i = 0; $i -lt 80; $i++) {
  $proc.Refresh()
  if ($proc.MainWindowHandle -ne 0) {
    $candidate = [System.Windows.Automation.AutomationElement]::FromHandle([IntPtr]$proc.MainWindowHandle)
    if ($null -ne $candidate) {
      $window = $candidate
      break
    }
  }
  Start-Sleep -Milliseconds 100
}

if ($null -eq $window) {
  [pscustomobject]@{
    ok = $false
    action = 'notepad-safe-type-test'
    method = 'uia-target-discovery'
    text_set = $false
    readback_exact = $false
    reason = 'notepad UIA window not found'
    process_id = $proc.Id
  } | ConvertTo-Json -Compress
  exit 0
}

$target = $null
$all = $window.FindAll(
  [System.Windows.Automation.TreeScope]::Descendants,
  [System.Windows.Automation.Condition]::TrueCondition
)
for ($i = 0; $i -lt $all.Count; $i++) {
  $item = $all.Item($i)
  $className = $item.Current.ClassName
  $nativeHwnd = $item.Current.NativeWindowHandle
  if ($nativeHwnd -ne 0 -and ($className -eq 'Edit' -or $className -like 'RichEdit*')) {
    $target = $item
    break
  }
}

if ($null -eq $target) {
  [pscustomobject]@{
    ok = $false
    action = 'notepad-safe-type-test'
    method = 'uia-target-discovery'
    text_set = $false
    readback_exact = $false
    reason = 'notepad native edit control not found through UIA'
    process_id = $proc.Id
    main_window_handle = $proc.MainWindowHandle
  } | ConvertTo-Json -Compress
  exit 0
}

[pscustomobject]@{
  ok = $true
  action = 'notepad-safe-type-test'
  method = 'uia-target-discovery'
  text_set = $false
  readback_exact = $false
  process_id = $proc.Id
  main_window_handle = $proc.MainWindowHandle
  edit_window_handle = $target.Current.NativeWindowHandle
  control_name = $target.Current.Name
  control_class = $target.Current.ClassName
  control_type = $target.Current.ControlType.ProgrammaticName
} | ConvertTo-Json -Compress
"""


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
    try:
        payload = run_powershell_json(notepad_uia_script())
        if payload.get("ok"):
            edit_hwnd = int(payload["edit_window_handle"])
            set_result = set_window_text(edit_hwnd, TEST5_TEXT)
            readback = get_window_text(edit_hwnd)
            exact = readback == TEST5_TEXT
            payload.update(
                {
                    "ok": exact,
                    "method": "uia-native-hwnd-wm-settext",
                    "text_set": True,
                    "set_message_result": set_result,
                    "readback_exact": exact,
                    "expected_text": TEST5_TEXT,
                    "readback": readback,
                }
            )
    except Exception as exc:
        payload = {
            "ok": False,
            "action": "notepad-safe-type-test",
            "method": "uia-native-hwnd-wm-settext",
            "text_set": False,
            "readback_exact": False,
            "error": str(exc),
        }

    try:
        screenshot = take_screenshot()
    except Exception as exc:
        screenshot = {"ok": False, "error": str(exc)}
    payload["screenshot"] = screenshot
    return payload


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
