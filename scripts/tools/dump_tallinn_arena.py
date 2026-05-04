import json
import subprocess

def dump_arena_state(target_file):
    cmd = [r"target\release\replayshark.exe", "-g", r"C:\Games\World_of_Warships", "dump", target_file]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)
    
    for line in process.stdout:
        if "OnArenaStateReceived" in line:
            with open("tallinn_arena_state.json", "w") as f:
                f.write(line)
            print("Saved tallinn_arena_state.json")
            break
    process.terminate()

dump_arena_state(r"C:\Users\arch\Downloads\20260416_212807_PRSC208-Tallin_15_NE_north.wowsreplay")
