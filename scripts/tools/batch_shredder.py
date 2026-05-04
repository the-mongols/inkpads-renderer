import os
import json
from pathlib import Path
from shredder import ReplayShredder
from tactical_renderer import TacticalRenderer

def main():
    REPLAY_DIR = Path("replays")
    OUTPUT_DIR = Path("output")
    EXE = r"c:\Users\arch\Documents\weegeeDev\attempt2\target\release\replayshark.exe"
    GAME = r"C:\Games\World_of_Warships"
    
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    replays = list(REPLAY_DIR.glob("*.wowsreplay"))
    print(f"Found {len(replays)} replays to process.")
    
    for replay in replays:
        print(f"\n>>> Processing: {replay.name}")
        try:
            # 1. Shred
            shredder = ReplayShredder(str(replay), EXE, GAME)
            report = shredder.run()
            
            report_name = replay.stem + "_report.json"
            report_path = OUTPUT_DIR / report_name
            with open(report_path, "w") as f:
                json.dump(report, f, indent=4)
            
            # 2. Render
            image_name = replay.stem + "_forensic.png"
            image_path = OUTPUT_DIR / image_name
            renderer = TacticalRenderer(report_path, output_path=image_path)
            renderer.render()
            
            print(f"Done: {image_name}")
            
        except Exception as e:
            print(f"FAILED {replay.name}: {e}")

if __name__ == "__main__":
    main()
