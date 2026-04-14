import os, time, json, requests, subprocess, pyautogui, psutil
from PIL import ImageGrab
import sys

# CONFIGURATION
TOKEN = sys.argv[1] if len(sys.argv) > 1 else ""
REPO = "thekung62b-jpg/wealth-machine"
CMD_FILE = "commands.json"
OUT_FILE = "output.json"
GITHUB_API = f"https://api.github.com/repos/{REPO}/contents/{CMD_FILE}"

print(f"--- V2 NEURAL LINK ACTIVE ---")
print(f"LISTENING ON {os.getenv('COMPUTERNAME')}...")

last_id = ""

def take_screenshot():
    ss = ImageGrab.grab()
    ss.save("last_frame.png")
    return "SCREENSHOT_SAVED"

while True:
    try:
        headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3.raw"}
        r = requests.get(GITHUB_API, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("id") != last_id:
                cmd_id, action = data.get("id"), data.get("cmd")
                print(f"EXECUTE[{cmd_id}]: {action}")
                result = "Unknown Action"
                
                if action == "screenshot": result = take_screenshot()
                elif action.startswith("click "):
                    x, y = map(int, action.split(" ")[1].split(","))
                    pyautogui.click(x, y); result = f"Clicked {x},{y}"
                elif action.startswith("type "):
                    pyautogui.write(action.replace("type ", ""), interval=0.1); result = "Typed"
                else:
                    proc = subprocess.run(action, shell=True, capture_output=True, text=True)
                    result = proc.stdout if proc.stdout else proc.stderr

                # Write the local receipt
                with open(OUT_FILE, "w") as f:
                    json.dump({"id": cmd_id, "result": result, "status": "done"}, f)
                last_id = cmd_id
                
                # DIAGNOSTIC PUSH
                print("Attempting to push...")
                push_cmd = f'git add . && git commit -m "Result {cmd_id}" && git pull origin master --no-rebase && git push https://{TOKEN}@github.com/{REPO}.git master'
                push_result = subprocess.run(push_cmd, shell=True, capture_output=True, text=True)
                print(f"GIT STDOUT: {push_result.stdout}")
                print(f"GIT STDERR: {push_result.stderr}")

        time.sleep(5)
    except Exception as e:
        print(f"Link Error: {e}"); time.sleep(5)