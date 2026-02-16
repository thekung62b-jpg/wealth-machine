# Little Homie's Direct Bridge Launcher - v1.0
# Mission: Bypass broken npm installers and link directly to Cloud Brain

import os
import subprocess
import sys

def launch_bridge():
    print("🚀 Little Homie Bridge Launcher Starting...")
    print("🛡️ Bypassing standard installers...")
    
    # Direct command to run the node via npx without local installation drama
    # Using the --yes flag to skip prompts and the specific version to avoid 'llama.cpp' builds
    cmd = ["npx", "--yes", "openclaw@6", "node", "pairing"]
    
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print("📡 Connecting to Gateway... Please wait for Pairing Code.")
        
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(output.strip())
                if "Pairing Code:" in output:
                    print("\n🎯 FOUND IT! COPY THE CODE ABOVE AND PASTE IN CHAT.")
                    
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    launch_bridge()
