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

Action: notepad-safe-click-test
- places the cursor at the end of TEST 5 text and inserts the TEST 6 line

Action: notepad-safe-save-test
- saves TEST 6 content from Notepad as control_test.txt and reads it back

Action: browser-example-click-test
- clicks once inside the visible Example Domain page before invoking the link through UIA

Action: browser-example-uia-dump
- dumps UIA descendants from the Example Domain Edge window whose names contain More

No keystrokes or credential automation.
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
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psutil
from PIL import ImageGrab


ROOT = Path(__file__).resolve().parents[1]
LAST_FRAME_FILE = ROOT / "last_frame.png"
TEST5_TEXT = "LITTLE HOMIE CONTROL TEST PASS"
TEST6_LINE = "CLICK TEST PASS"
TEST6_TEXT = f"{TEST5_TEXT}\r\n{TEST6_LINE}"
CONTROL_TEST_FILE = ROOT / "control_test.txt"
EXAMPLE_URL = "https://example.com"


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


def visible_windows() -> list[dict[str, Any]]:
    if os.name != "nt":
        raise RuntimeError("window enumeration is Windows-only")

    class RECT(ctypes.Structure):
        _fields_ = [
            ("left", ctypes.c_long),
            ("top", ctypes.c_long),
            ("right", ctypes.c_long),
            ("bottom", ctypes.c_long),
        ]

    user32 = ctypes.windll.user32
    windows: list[dict[str, Any]] = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def enum_proc(hwnd: int, _lparam: int) -> bool:
        if not user32.IsWindowVisible(hwnd):
            return True
        title_len = user32.GetWindowTextLengthW(hwnd)
        title_buf = ctypes.create_unicode_buffer(max(title_len + 1, 512))
        user32.GetWindowTextW(hwnd, title_buf, len(title_buf))
        title = title_buf.value
        if not title:
            return True
        rect = RECT()
        if not user32.GetWindowRect(ctypes.c_void_p(hwnd), ctypes.byref(rect)):
            return True
        windows.append(
            {
                "hwnd": int(hwnd),
                "title": title,
                "left": int(rect.left),
                "top": int(rect.top),
                "right": int(rect.right),
                "bottom": int(rect.bottom),
            }
        )
        return True

    user32.EnumWindows(enum_proc, 0)
    return windows


def click_screen_coordinate(x: int, y: int) -> None:
    user32 = ctypes.windll.user32
    user32.SetCursorPos(x, y)
    time.sleep(0.1)
    user32.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(0.05)
    user32.mouse_event(0x0004, 0, 0, 0, 0)


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


def send_window_message_int(hwnd: int, message: int, wparam: int, lparam: int) -> int:
    user32 = ctypes.windll.user32
    user32.SendMessageW.argtypes = None
    user32.SendMessageW.restype = ctypes.c_ssize_t
    return int(user32.SendMessageW(ctypes.c_void_p(hwnd), message, wparam, lparam))


def set_window_text(hwnd: int, text: str) -> int:
    return send_window_message(hwnd, 0x000C, 0, ctypes.c_wchar_p(text))


def set_text_selection(hwnd: int, start: int, end: int) -> int:
    return send_window_message(hwnd, 0x00B1, start, end)


def replace_text_selection(hwnd: int, text: str) -> int:
    return send_window_message(hwnd, 0x00C2, 1, ctypes.c_wchar_p(text))


def save_notepad_window(hwnd: int) -> int:
    return send_window_message_int(hwnd, 0x0111, 3, 0)


def get_window_text(hwnd: int) -> str:
    length = send_window_message(hwnd, 0x000E, 0, 0)
    buffer = ctypes.create_unicode_buffer(max(length + 1, len(TEST6_TEXT) + 1))
    send_window_message(hwnd, 0x000D, len(buffer), buffer)
    return buffer.value


def notepad_uia_script(file_path: Path | None = None) -> str:
    if file_path is None:
        start_process = "$proc = Start-Process notepad.exe -PassThru"
    else:
        escaped_path = str(file_path).replace("'", "''")
        start_process = f"$proc = Start-Process notepad.exe -ArgumentList '{escaped_path}' -PassThru"

    return """
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

__START_PROCESS__
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
""".replace("__START_PROCESS__", start_process)


def read_control_test_file() -> str:
    data = CONTROL_TEST_FILE.read_bytes()
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("utf-16")


def browser_example_link_script() -> str:
    return """
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$root = [System.Windows.Automation.AutomationElement]::RootElement
$link = $null
$all = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
for ($i = 0; $i -lt $all.Count; $i++) {
  $item = $all.Item($i)
  if ($item.Current.Name -like '*More information*') {
    $link = $item
    break
  }
}

$clickExecuted = $false
if ($null -ne $link) {
  $pattern = $null
  if ($link.TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern, [ref]$pattern)) {
    ([System.Windows.Automation.InvokePattern]$pattern).Invoke()
    $clickExecuted = $true
  }
}

Start-Sleep -Seconds 6
$root = [System.Windows.Automation.AutomationElement]::RootElement
$dest = $false
$destEvidence = @()
$after = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
for ($i = 0; $i -lt $after.Count; $i++) {
  $name = $after.Item($i).Current.Name
  if ($name -like '*Example Domains*' -or $name -like '*iana.org/domains/example*' -or $name -like '*IANA-managed Reserved Domains*') {
    $dest = $true
    $destEvidence += $name
    if ($destEvidence.Count -ge 5) {
      break
    }
  }
}

[pscustomobject]@{
  ok = $clickExecuted -and $dest
  action = 'browser-example-click-test'
  method = 'coordinate-page-activation-then-uia-link-invoke'
  link_found = $null -ne $link
  link_name = if ($null -ne $link) { $link.Current.Name } else { '' }
  click_action_executed = $clickExecuted
  browser_navigated_after_click = $dest
  expected_destination_confirmed = $dest
  destination_evidence = $destEvidence
} | ConvertTo-Json -Compress -Depth 4
"""


def browser_example_uia_dump_script() -> str:
    return """
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$edge = Get-Process msedge -ErrorAction SilentlyContinue |
  Where-Object { $_.MainWindowHandle -ne 0 } |
  Sort-Object @{Expression = { $_.MainWindowTitle -like '*Example Domain*' }; Descending = $true}, StartTime -Descending |
  Select-Object -First 1

if ($null -eq $edge) {
  [pscustomobject]@{
    ok = $false
    action = 'browser-example-uia-dump'
    method = 'active-edge-window-uia-descendant-name-dump'
    edge_window_found = $false
    scanned_descendants = 0
    contains_more_name = $false
    more_matches = @()
  } | ConvertTo-Json -Compress -Depth 4
  exit 0
}

$window = [System.Windows.Automation.AutomationElement]::FromHandle([IntPtr]$edge.MainWindowHandle)
$all = $window.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
$matches = @()
for ($i = 0; $i -lt $all.Count; $i++) {
  $item = $all.Item($i)
  $name = $item.Current.Name
  if ($name -like '*More*') {
    $matches += [pscustomobject]@{
      name = $name
      class = $item.Current.ClassName
      control_type = $item.Current.ControlType.ProgrammaticName
      hwnd = $item.Current.NativeWindowHandle
    }
  }
}

[pscustomobject]@{
  ok = $true
  action = 'browser-example-uia-dump'
  method = 'active-edge-window-uia-descendant-name-dump'
  edge_window_found = $true
  edge_process_id = $edge.Id
  edge_title = $edge.MainWindowTitle
  scanned_descendants = $all.Count
  contains_more_name = $matches.Count -gt 0
  more_matches = $matches
} | ConvertTo-Json -Compress -Depth 4
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


def notepad_safe_click_test() -> dict[str, Any]:
    try:
        payload = run_powershell_json(notepad_uia_script())
        if payload.get("ok"):
            edit_hwnd = int(payload["edit_window_handle"])
            set_result = set_window_text(edit_hwnd, TEST5_TEXT)
            place_result = set_text_selection(edit_hwnd, len(TEST5_TEXT), len(TEST5_TEXT))
            insert_result = replace_text_selection(edit_hwnd, f"\r\n{TEST6_LINE}")
            readback = get_window_text(edit_hwnd)
            exact = readback == TEST6_TEXT
            payload.update(
                {
                    "ok": exact,
                    "method": "uia-native-hwnd-em-setsel-replacesel",
                    "initial_text_set": set_result == 1,
                    "placement_action_executed": True,
                    "placement_message_result": place_result,
                    "insert_message_result": insert_result,
                    "second_line_present": TEST6_LINE in readback,
                    "readback_exact": exact,
                    "expected_text": TEST6_TEXT,
                    "readback": readback,
                }
            )
    except Exception as exc:
        payload = {
            "ok": False,
            "action": "notepad-safe-click-test",
            "method": "uia-native-hwnd-em-setsel-replacesel",
            "placement_action_executed": False,
            "second_line_present": False,
            "readback_exact": False,
            "error": str(exc),
        }

    try:
        screenshot = take_screenshot()
    except Exception as exc:
        screenshot = {"ok": False, "error": str(exc)}
    payload["action"] = "notepad-safe-click-test"
    payload["screenshot"] = screenshot
    return payload


def notepad_safe_save_test() -> dict[str, Any]:
    expected = TEST6_TEXT
    try:
        CONTROL_TEST_FILE.write_text("", encoding="utf-8")
        payload = run_powershell_json(notepad_uia_script(CONTROL_TEST_FILE))
        if payload.get("ok"):
            main_hwnd = int(payload["main_window_handle"])
            edit_hwnd = int(payload["edit_window_handle"])
            set_result = set_window_text(edit_hwnd, expected)
            save_result = save_notepad_window(main_hwnd)
            readback = ""
            read_success = False
            for _ in range(20):
                readback = read_control_test_file()
                read_success = True
                if readback == expected:
                    break
                time.sleep(0.1)

            exact = read_success and readback == expected
            payload.update(
                {
                    "ok": exact,
                    "action": "notepad-safe-save-test",
                    "method": "uia-native-hwnd-wm-settext-wm-command-save",
                    "file_path": str(CONTROL_TEST_FILE),
                    "notepad_text_set": set_result == 1,
                    "save_command_result": save_result,
                    "file_saved_successfully": CONTROL_TEST_FILE.exists() and CONTROL_TEST_FILE.stat().st_size > 0,
                    "shell_readback_succeeded": read_success,
                    "readback_exact": exact,
                    "expected_text": expected,
                    "readback": readback,
                }
            )
    except Exception as exc:
        payload = {
            "ok": False,
            "action": "notepad-safe-save-test",
            "method": "uia-native-hwnd-wm-settext-wm-command-save",
            "file_saved_successfully": False,
            "shell_readback_succeeded": False,
            "readback_exact": False,
            "error": str(exc),
        }

    try:
        screenshot = take_screenshot()
    except Exception as exc:
        screenshot = {"ok": False, "error": str(exc)}
    payload["screenshot"] = screenshot
    return payload


def browser_example_click_test() -> dict[str, Any]:
    activation_click: dict[str, Any] = {"executed": False}
    try:
        os.startfile(EXAMPLE_URL)
        time.sleep(5)
        example_window = next(
            (window for window in visible_windows() if "Example Domain" in window["title"]),
            None,
        )
        if example_window:
            width = example_window["right"] - example_window["left"]
            height = example_window["bottom"] - example_window["top"]
            x = example_window["left"] + int(width * 0.82)
            y = example_window["top"] + int(height * 0.28)
            click_screen_coordinate(x, y)
            activation_click = {
                "executed": True,
                "x": x,
                "y": y,
                "window": example_window,
            }
            time.sleep(1)

        payload = run_powershell_json(browser_example_link_script())
        payload["page_activation_click"] = activation_click
    except Exception as exc:
        payload = {
            "ok": False,
            "action": "browser-example-click-test",
            "method": "coordinate-page-activation-then-uia-link-invoke",
            "click_action_executed": False,
            "browser_navigated_after_click": False,
            "expected_destination_confirmed": False,
            "page_activation_click": activation_click,
            "error": str(exc),
        }

    try:
        screenshot = take_screenshot()
    except Exception as exc:
        screenshot = {"ok": False, "error": str(exc)}
    payload["screenshot"] = screenshot
    return payload


def browser_example_uia_dump() -> dict[str, Any]:
    try:
        payload = run_powershell_json(browser_example_uia_dump_script())
    except Exception as exc:
        payload = {
            "ok": False,
            "action": "browser-example-uia-dump",
            "method": "active-edge-window-uia-descendant-name-dump",
            "edge_window_found": False,
            "scanned_descendants": 0,
            "contains_more_name": False,
            "more_matches": [],
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
        choices=[
            "probe",
            "active-window",
            "notepad-safe-type-test",
            "notepad-safe-click-test",
            "notepad-safe-save-test",
            "browser-example-click-test",
            "browser-example-uia-dump",
        ],
        help="Supported actions: probe, active-window, notepad-safe-type-test, notepad-safe-click-test, notepad-safe-save-test, browser-example-click-test, browser-example-uia-dump",
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
        if args.action == "notepad-safe-click-test":
            print(json.dumps(notepad_safe_click_test(), separators=(",", ":")))
            return 0
        if args.action == "notepad-safe-save-test":
            print(json.dumps(notepad_safe_save_test(), separators=(",", ":")))
            return 0
        if args.action == "browser-example-click-test":
            print(json.dumps(browser_example_click_test(), separators=(",", ":")))
            return 0
        if args.action == "browser-example-uia-dump":
            print(json.dumps(browser_example_uia_dump(), separators=(",", ":")))
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
