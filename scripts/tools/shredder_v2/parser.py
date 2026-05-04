import json
import subprocess
from pathlib import Path

class ReplayParser:
    """
    Orchestrates the raw telemetry stream from replayshark.
    Dispatches packets to registered handlers.
    """
    def __init__(self, replayshark_exe, game_dir):
        self.exe = replayshark_exe
        self.game_dir = game_dir
        self.handlers = []

    def register_handler(self, handler_func):
        self.handlers.append(handler_func)

    def run(self, replay_path):
        print(f"[Parser] Shredding {Path(replay_path).name}...")
        
        cmd = [self.exe, "-g", self.game_dir, "dump", str(replay_path)]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True, encoding='utf-8')
        
        for line in process.stdout:
            try:
                data = json.loads(line)
                clock = data.get("clock", 0)
                payload = data.get("payload", {})
                
                # Check for header
                if "mapName" in data:
                    self._dispatch("header", data, 0)
                    continue

                # Dispatch standard packets
                for p_type, p_data in payload.items():
                    self._dispatch(p_type, p_data, clock)
                    
            except json.JSONDecodeError:
                continue
            except Exception as e:
                # Targeted logging instead of silent failure
                # print(f"[Parser] Error on clock {clock}: {e}")
                continue
        
        process.wait()
        self._dispatch("finalize", {}, 0)

    def _dispatch(self, packet_type, data, clock):
        for handler in self.handlers:
            handler(packet_type, data, clock)
