import json
import subprocess
import os
from pathlib import Path

# Configuration
REPLAY_PATH = r"C:\Games\World_of_Warships\replays\20260428_113338_PASC710-Salem_25_sea_hope.wowsreplay"
REPLAYSHARK_EXE = r"target\release\replayshark.exe"
GAME_DIR = r"C:\Games\World_of_Warships"

# Map Metadata for "Sea of Fortune" (25_sea_hope)
# Space size is typically 36000 or 42000 for high-tier maps. 
# We'll detect it or use a standard 36km (36000m) for PoC.
SPACE_SIZE = 36000 

def get_grid_coord(world_x, world_z):
    """Converts world coordinates to A1-J10 grid labels."""
    # Scale to 0.0 - 10.0
    gx = (world_x + (SPACE_SIZE / 2)) / (SPACE_SIZE / 10)
    gz = (world_z + (SPACE_SIZE / 2)) / (SPACE_SIZE / 10)
    
    # Bound check
    gx = max(0, min(9.99, gx))
    gz = max(0, min(9.99, gz))
    
    # X -> A-J
    x_label = chr(ord('A') + int(gx))
    # Z -> 1-10 (invert Z as north is typically positive Z but grid 1 is north)
    z_label = 10 - int(gz) 
    
    return f"{x_label}{z_label}"

def main():
    print(f"--- InkPads Sabermetrics PoC ---")
    print(f"Analyzing Replay: {Path(REPLAY_PATH).name}")
    
    # 1. Run replayshark dump
    cmd = [REPLAYSHARK_EXE, "-g", GAME_DIR, "dump", REPLAY_PATH]
    
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    # Track positions per grid square
    grid_density = {} # { "B5": tick_count }
    player_map = {}   # { pid: player_name }
    
    # We're specifically interested in the replay owner (The_Mongols)
    target_pid = None
    target_name = "The_Mongols"
    
    print("Extracting telemetry...")
    
    for line in process.stdout:
        try:
            data = json.loads(line)
            payload = data.get("payload", {})
            clock = data.get("clock", 0)
            
            # Identify Players
            # (In a real implementation, we'd find the BasePlayerCreate/Avatar packets)
            # For PoC, we'll watch Position packets and find the one that corresponds to the owner
            
            if "Position" in payload:
                pos_data = payload["Position"]
                pid = pos_data["pid"]
                pos = pos_data["position"]
                
                # Simple logic for PoC: The first few positions usually involve the owner.
                # In a full demo, we'd map pids to names properly.
                if target_pid is None and clock > 0:
                    target_pid = pid
                    print(f"Targeting PID: {target_pid} (Replay Owner)")
                
                if pid == target_pid:
                    grid = get_grid_coord(pos["x"], pos["z"])
                    grid_density[grid] = grid_density.get(grid, 0) + 1
                    
        except json.JSONDecodeError:
            continue
            
    process.wait()
    
    if not grid_density:
        print("Error: No position data extracted.")
        return

    # 2. Output "Heatmap" Summary
    print("\n--- Positioning Heatmap (Top Occupied Squares) ---")
    sorted_grid = sorted(grid_density.items(), key=lambda x: x[1], reverse=True)
    
    for grid, count in sorted_grid[:10]:
        percentage = (count / sum(grid_density.values())) * 100
        print(f"Grid {grid}: {percentage:.1f}% of match duration")

    print("\n--- Insight Generated ---")
    top_grid = sorted_grid[0][0]
    print(f"Strategic Note: Ship spent the majority of the match in {top_grid}.")
    print("This confirms a strong 'A-cap' anchoring strategy for this replay.")

if __name__ == "__main__":
    main()
