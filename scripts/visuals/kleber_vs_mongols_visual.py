import json
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math

# Configuration
REPLAY_PATH = r"C:\Users\arch\Downloads\20260428_184026_PFSD110-Kleber_04_Archipelago.wowsreplay"
REPLAYSHARK_EXE = r"target\release\replayshark.exe"
GAME_DIR = r"C:\Games\World_of_Warships"

# Map Metadata (Archipelago)
SPACE_SIZE = 1000 
MAP_SIZE_PX = 760 

# Asset Paths
ASSETS_DIR = Path("assets/maps/04_Archipelago/spaces/04_Archipelago")
WATER_IMG = ASSETS_DIR / "minimap_water.png"
LAND_IMG = ASSETS_DIR / "minimap.png"
OUTPUT_IMG = Path("kleber_vs_mongols_spotted.png")

def world_to_pixel(world_x, world_z):
    scale = MAP_SIZE_PX / SPACE_SIZE
    half = MAP_SIZE_PX / 2
    px = (world_x * scale) + half
    py = ((-world_z) * scale) + half
    return int(px), int(py)

def main():
    print("--- InkPads Visual Sabermetrics: Owner vs. Spotted ---")
    
    # 1. Create Base Map
    water = Image.open(WATER_IMG).convert("RGBA")
    land = Image.open(LAND_IMG).convert("RGBA")
    base_map = Image.alpha_composite(water, land)
    
    # 2. Extract Data
    pids = {
        645361: {"name": "TheStrategyNerd (Kleber)", "points": [], "tel": [], "last": None, "color": (0, 255, 255)}, # Cyan
        645359: {"name": "The_Mongols (Opponent)", "points": [], "tel": [], "last": None, "color": (255, 50, 255)}  # Magenta
    }
    
    cmd = [REPLAYSHARK_EXE, "-g", GAME_DIR, "dump", REPLAY_PATH]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)
    
    for line in process.stdout:
        try:
            data = json.loads(line)
            payload = data.get("payload", {})
            clock = data.get("clock", 0)
            
            pos_data = None
            if "Position" in payload:
                pos_data = payload["Position"]
            elif "PlayerOrientation" in payload:
                pos_data = payload["PlayerOrientation"]
                
            if pos_data:
                pid = pos_data.get("pid")
                if pid in pids:
                    pos = pos_data["position"]
                    curr_p = world_to_pixel(pos["x"], pos["z"])
                    
                    p_info = pids[pid]
                    p_info["points"].append(curr_p)
                    
                    if p_info["last"] is not None:
                        duration = clock - p_info["last"]
                        if duration > 0:
                            p_info["tel"].append((curr_p[0], curr_p[1], duration))
                    p_info["last"] = clock
        except: continue
    process.wait()

    # 3. High-Fidelity Rendering (4x SSAA)
    RENDER_SCALE = 4
    HI_RES = MAP_SIZE_PX * RENDER_SCALE
    
    final_img = base_map.resize((HI_RES, HI_RES), Image.Resampling.LANCZOS)
    
    for pid, p_info in pids.items():
        if not p_info["points"]: continue
        
        print(f"Rendering {p_info['name']} with {len(p_info['points'])} points...")
        
        heat_layer = Image.new("RGBA", (HI_RES, HI_RES), (0,0,0,0))
        path_layer = Image.new("RGBA", (HI_RES, HI_RES), (0,0,0,0))
        heat_draw = ImageDraw.Draw(heat_layer)
        path_draw = ImageDraw.Draw(path_layer)
        
        # Max dwell for scaling
        max_d = max([d for x, y, d in p_info["tel"]]) if p_info["tel"] else 1
        
        # Heat
        for x, y, duration in p_info["tel"]:
            hx, hy = x * RENDER_SCALE, y * RENDER_SCALE
            r = 15 * RENDER_SCALE
            intensity = min(1.0, math.sqrt(duration / max_d)) if max_d > 0 else 0
            a = int(30 + (intensity * 150))
            heat_draw.ellipse([hx-r, hy-r, hx+r, hy+r], fill=(*p_info["color"], a))
            
        # Path with "Spotted" jump detection
        # We draw segments only if clock jump is < 5s
        p_list = p_info["points"]
        # Need to correlate clock with points for jump detection
        # But for this simple script, we'll just check distance between points as a proxy
        # or just draw the full line for now but notice gaps.
        # Let's just draw the line segments.
        for i in range(1, len(p_list)):
            p1 = p_list[i-1]
            p2 = p_list[i]
            
            # Simple distance threshold: if move is > 10% of map, it's a jump
            dist = math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)
            if dist < 50: # Normal movement
                path_draw.line([(p1[0]*RENDER_SCALE, p1[1]*RENDER_SCALE), 
                                (p2[0]*RENDER_SCALE, p2[1]*RENDER_SCALE)], 
                               fill=(0, 0, 0, 150), width=6 * RENDER_SCALE)
                path_draw.line([(p1[0]*RENDER_SCALE, p1[1]*RENDER_SCALE), 
                                (p2[0]*RENDER_SCALE, p2[1]*RENDER_SCALE)], 
                               fill=(*p_info["color"], 255), width=2 * RENDER_SCALE)

        heat_layer = heat_layer.filter(ImageFilter.GaussianBlur(radius=8 * RENDER_SCALE))
        final_img.paste(heat_layer, (0, 0), heat_layer)
        final_img.paste(path_layer, (0, 0), path_layer)

    # 4. Finish
    output_img = final_img.resize((MAP_SIZE_PX, MAP_SIZE_PX), Image.Resampling.LANCZOS)
    output_img = output_img.filter(ImageFilter.SHARPEN)
    
    draw = ImageDraw.Draw(output_img)
    grid_color = (255, 255, 255, 60)
    for i in range(1, 10):
        off = i * (MAP_SIZE_PX / 10)
        draw.line([(off, 0), (off, MAP_SIZE_PX)], fill=grid_color, width=1)
        draw.line([(0, off), (MAP_SIZE_PX, off)], fill=grid_color, width=1)

    output_img = output_img.convert("RGB")
    output_img.save(OUTPUT_IMG, quality=95)
    print(f"Success! Comparison saved to: {OUTPUT_IMG.resolve()}")

if __name__ == "__main__":
    main()
