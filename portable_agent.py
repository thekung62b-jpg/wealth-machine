import os
import sys
import time
import json
import subprocess
from urllib.request import Request, urlopen

# Portable Python Agent - No Dependencies (Token as Argument)
REPO = "thekung62b-jpg/wealth-machine"

def get_cmd(token):
    req = Request(f"https://api.github.com/repos/{REPO}/contents/commands.json")
    req.add_header('Authorization', f'token {token}')
    with urlopen(req) as r:
        data = json.loads(r.read().decode())
        import base64
        return json.loads(base64.b64decode(data['content']).decode())

def run(token):
    print("📡 Portable Agent: LISTENING...")
    last_id = ""
    while True:
        try:
            cmd_data = get_cmd(token)
            if cmd_data['id'] != last_id:
                print(f"📥 EXECUTE: {cmd_data['cmd']}")
                subprocess.run(cmd_data['cmd'], shell=True)
                last_id = cmd_data['id']
        except: pass
        time.sleep(3)

if __name__ == "__main__":
    if len(sys.argv) > 1: run(sys.argv[1])
    else: print("Usage: python agent.py <github_token>")
