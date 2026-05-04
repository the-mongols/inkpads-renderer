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

def world_to_pixel(world_x, world_z):
    scale = MAP_SIZE_PX / SPACE_SIZE
    half = MAP_SIZE_PX / 2
    px = (world_x * scale) + half
    py = ((-world_z) * scale) + half
    return int(px), int(py)

def get_telemetry():
    pids = {
        645361: {"name": "Kleber (Owner)", "data": []},
        645359: {"name": "Marceau (The_Mongols)", "data": []}
    }
    
    cmd = [REPLAYSHARK_EXE, "-g", GAME_DIR, "dump", REPLAY_PATH]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)
    
    last_states = {} # pid -> (clock, x, z)
    
    for line in process.stdout:
        try:
            data = json.loads(line)
            payload = data.get("payload", {})
            clock = data.get("clock", 0)
            
            pos_data = None
            if "Position" in payload: pos_data = payload["Position"]
            elif "PlayerOrientation" in payload: pos_data = payload["PlayerOrientation"]
            
            if pos_data:
                pid = pos_data.get("pid")
                if pid in pids:
                    pos = pos_data["position"]
                    px, pz = pos["x"], pos["z"]
                    
                    if pid in last_states:
                        prev_clock, prev_x, prev_z = last_states[pid]
                        dt = clock - prev_clock
                        if dt > 0:
                            dist = math.sqrt((px - prev_x)**2 + (pz - prev_z)**2)
                            speed = dist / dt
                            # Heat weight = Presence duration / Speed
                            # If speed is 0 (beached), weight is very high.
                            # We clamp speed to a minimum to avoid div by zero.
                            weight = dt / (speed + 0.05)
                            
                            p_x, p_y = world_to_pixel(px, pz)
                            pids[pid]["data"].append({"x": p_x, "y": p_y, "weight": weight, "dt": dt})
                            
                    last_states[pid] = (clock, px, pz)
        except: continue
    process.wait()
    return pids

def render_heat(name, data, color, output_path, base_map):
    print(f"Rendering {name} heatmap...")
    RENDER_SCALE = 4
    HI_RES = MAP_SIZE_PX * RENDER_SCALE
    
    heat_layer = Image.new("RGBA", (HI_RES, HI_RES), (0,0,0,0))
    draw = ImageDraw.Draw(heat_layer)
    
    if not data:
        print(f"No data for {name}")
        return
        
    # Find max weight for normalization
    max_w = max([d["weight"] for d in data])
    
    for pt in data:
        hx, hy = pt["x"] * RENDER_SCALE, pt["y"] * RENDER_SCALE
        # Radius of the "presence blob"
        r = 12 * RENDER_SCALE
        
        # Alpha based on relative weight (presence / speed)
        # We use a power function to emphasize the 'hot' areas (low speed)
        intensity = (pt["weight"] / max_w) ** 0.5
        alpha = int(20 + (intensity * 200))
        
        draw.ellipse([hx-r, hy-r, hx+r, hy+r], fill=(*color, alpha))
        
    # Apply soft blur
    heat_layer = heat_layer.filter(ImageFilter.GaussianBlur(radius=15 * RENDER_SCALE))
    
    # Composite
    final = base_map.resize((HI_RES, HI_RES), Image.Resampling.LANCZOS)
    final.paste(heat_layer, (0, 0), heat_layer)
    
    # Downscale
    output_img = final.resize((MAP_SIZE_PX, MAP_SIZE_PX), Image.Resampling.LANCZOS)
    output_img = output_img.filter(ImageFilter.SHARPEN)
    
    # Grid
    grid_draw = ImageDraw.Draw(output_img)
    for i in range(1, 10):
        off = i * (MAP_SIZE_PX / 10)
        grid_draw.line([(off, 0), (off, MAP_SIZE_PX)], fill=(255, 255, 255, 40), width=1)
        grid_draw.line([(0, off), (MAP_SIZE_PX, off)], fill=(255, 255, 255, 40), width=1)
        
    output_img.convert("RGB").save(output_path, quality=95)
    print(f"Saved: {output_path}")

def render_combined(pids, output_path, base_map):
    print(f"Rendering combined heatmap...")
    RENDER_SCALE = 4
    HI_RES = MAP_SIZE_PX * RENDER_SCALE
    
    combined_heat = Image.new("RGBA", (HI_RES, HI_RES), (0,0,0,0))
    
    # Colors: Owner = Green (Friendly), Mongols = Red (Foe)
    colors = {645361: (0, 255, 100), 645359: (255, 0, 50)}
    
    for pid, info in pids.items():
        if not info["data"]: continue
        
        layer = Image.new("RGBA", (HI_RES, HI_RES), (0,0,0,0))
        draw = ImageDraw.Draw(layer)
        max_w = max([d["weight"] for d in info["data"]])
        color = colors[pid]
        
        for pt in info["data"]:
            hx, hy = pt["x"] * RENDER_SCALE, pt["y"] * RENDER_SCALE
            r = 15 * RENDER_SCALE
            intensity = (pt["weight"] / max_w) ** 0.5
            alpha = int(20 + (intensity * 200))
            draw.ellipse([hx-r, hy-r, hx+r, hy+r], fill=(*color, alpha))
            
        layer = layer.filter(ImageFilter.GaussianBlur(radius=15 * RENDER_SCALE))
        combined_heat.paste(layer, (0, 0), layer)
        
    final = base_map.resize((HI_RES, HI_RES), Image.Resampling.LANCZOS)
    final.paste(combined_heat, (0, 0), combined_heat)
    
    output_img = final.resize((MAP_SIZE_PX, MAP_SIZE_PX), Image.Resampling.LANCZOS)
    output_img = output_img.filter(ImageFilter.SHARPEN)
    
    # Grid
    grid_draw = ImageDraw.Draw(output_img)
    for i in range(1, 10):
        off = i * (MAP_SIZE_PX / 10)
        grid_draw.line([(off, 0), (off, MAP_SIZE_PX)], fill=(255, 255, 255, 40), width=1)
        grid_draw.line([(0, off), (MAP_SIZE_PX, off)], fill=(255, 255, 255, 40), width=1)
        
    output_img.convert("RGB").save(output_path, quality=95)
    print(f"Saved: {output_path}")

def main():
    print("--- InkPads True Heat Engine (Velocity-Weighted) ---")
    
    # Load Base Map
    water = Image.open(WATER_IMG).convert("RGBA")
    land = Image.open(LAND_IMG).convert("RGBA")
    base_map = Image.alpha_composite(water, land)
    
    # Extract Telemetry
    pids = get_telemetry()
    
    # Image 1: Owner Only (Green-ish/Cyan Heat)
    render_heat("Kleber", pids[645361]["data"], (0, 255, 255), "owner_true_heat.png", base_map)
    
    # Image 2: Mongols Only (Magenta/Pink Heat)
    render_heat("Marceau", pids[645359]["data"], (255, 50, 255), "mongols_true_heat.png", base_map)
    
    # Image 3: Combined (Green vs Red)
    render_combined(pids, "combined_true_heat.png", base_map)

if __name__ == "__main__":
    main()
