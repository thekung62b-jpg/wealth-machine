import os
import sys
import time
import subprocess

# Little Homie Voice HQ - v1.1 (Clean)
TOKEN = sys.argv[1] if len(sys.argv) > 1 else None

def speak(text):
    print(f"🤖 LITTLE HOMIE: {text}")
    # Direct PowerShell Voice Synthesis
    cmd = f'powershell -Command "Add-Type –AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak(\'{text}\')"'
    subprocess.run(cmd, shell=True)

def run():
    os.system('cls' if os.name == 'nt' else 'clear')
    speak("Voice Link Established. I'm the cyber raven. I'm ready to build, Big Homie.")
    print("🎤 [READY] Speak to me in the Telegram/Chat window...")
    
    while True:
        # Keep process alive
        time.sleep(10)

if __name__ == "__main__":
    if TOKEN: run()
    else: print("Error: No Token Provided")
