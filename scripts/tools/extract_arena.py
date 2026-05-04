import json
import subprocess

REPLAY_PATH = r"C:\Games\World_of_Warships\replays\20260428_113338_PASC710-Salem_25_sea_hope.wowsreplay"
REPLAYSHARK_EXE = r"target\release\replayshark.exe"
GAME_DIR = r"C:\Games\World_of_Warships"

def main():
    cmd = [REPLAYSHARK_EXE, "-g", GAME_DIR, "dump", REPLAY_PATH]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)
    
    with open("arena_state.json", "w") as f:
        for line in process.stdout:
            try:
                data = json.loads(line)
                if "OnArenaStateReceived" in data.get("payload", {}):
                    json.dump(data, f)
                    break
            except: continue
    process.kill()

if __name__ == "__main__":
    main()
