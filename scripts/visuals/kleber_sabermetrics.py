import json
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# Configuration
REPLAY_PATH = r"C:\Users\arch\Downloads\20260428_184026_PFSD110-Kleber_04_Archipelago.wowsreplay"
REPLAYSHARK_EXE = r"target\release\replayshark.exe"
GAME_DIR = r"C:\Games\World_of_Warships"

# Map Metadata (Archipelago)
# minX="-7" maxX="6" -> 14 chunks -> (14-4)*100 = 1000 BigWorld Units
SPACE_SIZE = 1000 
MAP_SIZE_PX = 760  # Native game minimap size

# Asset Paths
ASSETS_DIR = Path("assets/maps/04_Archipelago/spaces/04_Archipelago")
WATER_IMG = ASSETS_DIR / "minimap_water.png"
LAND_IMG = ASSETS_DIR / "minimap.png"
OUTPUT_IMG = Path("kleber_sabermetrics.png")

def world_to_pixel(world_x, world_z):
    """Converts world coordinates (BigWorld units) to image pixel coordinates."""
    scale = MAP_SIZE_PX / SPACE_SIZE
    half = MAP_SIZE_PX / 2
    
    # Math from Rust: (pos.x * scale + half)
    px = (world_x * scale) + half
    py = ((-world_z) * scale) + half
    
    return int(px), int(py)

def main():
    print("--- InkPads Visual Sabermetrics Engine (Kleber 1v1) ---")
    
    # 1. Create Base Map
    if not WATER_IMG.exists() or not LAND_IMG.exists():
        print(f"Error: Map assets not found in {ASSETS_DIR}")
        return

    print("Compositing map assets...")
    water = Image.open(WATER_IMG).convert("RGBA")
    land = Image.open(LAND_IMG).convert("RGBA")
    base_map = Image.alpha_composite(water, land)
    
    # 2. Extract Data
    target_pid = 645359 # The_Mongols
    print(f"Extracting telemetry for The_Mongols (ID: {target_pid})...")
    
    cmd = [REPLAYSHARK_EXE, "-g", GAME_DIR, "dump", REPLAY_PATH]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)
    
    points = []
    telemetry_data = [] # (pixel_x, pixel_y, duration)
    last_clock = None
    
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
                
            if pos_data and pos_data.get("pid") == target_pid:
                pos = pos_data["position"]
                curr_p = world_to_pixel(pos["x"], pos["z"])
                points.append(curr_p)
                
                if last_clock is not None:
                    duration = max(0, clock - last_clock)
                    telemetry_data.append((curr_p[0], curr_p[1], duration))
                
                last_clock = clock
                    
        except: continue
    process.wait()
    
    if not points:
        print("Error: No telemetry found for target ID.")
        return

    # 3. High-Fidelity Rendering (4x Supersampling)
    print(f"Generating High-Fidelity Tactical Visuals (4x SSAA) for {len(points)} points...")
    RENDER_SCALE = 4
    HI_RES = MAP_SIZE_PX * RENDER_SCALE
    
    # Create Hi-Res layers
    hi_res_heat = Image.new("RGBA", (HI_RES, HI_RES), (0,0,0,0))
    hi_res_path = Image.new("RGBA", (HI_RES, HI_RES), (0,0,0,0))
    heat_draw = ImageDraw.Draw(hi_res_heat)
    path_draw = ImageDraw.Draw(hi_res_path)
    
    # Layer 1: Heat Blobs (Additive Neon Orange)
    for x, y, duration in telemetry_data:
        hx, hy = x * RENDER_SCALE, y * RENDER_SCALE
        r = 20 * RENDER_SCALE 
        # Weighted by duration
        a = min(180, 50 + int(duration * 200))
        if a > 0:
            heat_draw.ellipse([hx-r, hy-r, hx+r, hy+r], fill=(255, 80, 0, a))
            
    # Layer 2: Glowing Cyan Path
    if len(points) > 1:
        scaled_points = [(p[0] * RENDER_SCALE, p[1] * RENDER_SCALE) for p in points]
        # Dark outer glow
        path_draw.line(scaled_points, fill=(0, 0, 0, 200), width=10 * RENDER_SCALE)
        # Main Cyan line
        path_draw.line(scaled_points, fill=(0, 255, 255, 255), width=3 * RENDER_SCALE)

    # 4. Composite & Downscale
    print("Compositing and filtering...")
    hi_res_heat = hi_res_heat.filter(ImageFilter.GaussianBlur(radius=8 * RENDER_SCALE))
    
    final_base = base_map.resize((HI_RES, HI_RES), Image.Resampling.LANCZOS)
    final_base.paste(hi_res_heat, (0, 0), hi_res_heat)
    final_base.paste(hi_res_path, (0, 0), hi_res_path)
    
    output_img = final_base.resize((MAP_SIZE_PX, MAP_SIZE_PX), Image.Resampling.LANCZOS)
    output_img = output_img.filter(ImageFilter.SHARPEN)
    
    # 5. Add Grid Overlay
    draw = ImageDraw.Draw(output_img)
    grid_color = (255, 255, 255, 80)
    for i in range(1, 10):
        offset = i * (MAP_SIZE_PX / 10)
        draw.line([(offset, 0), (offset, MAP_SIZE_PX)], fill=grid_color, width=1)
        draw.line([(0, offset), (MAP_SIZE_PX, offset)], fill=grid_color, width=1)

    # 6. Save & Finish
    output_img = output_img.convert("RGB")
    output_img.save(OUTPUT_IMG, quality=95)
    print(f"Success! High-Fidelity Heatmap saved to: {OUTPUT_IMG.resolve()}")

if __name__ == "__main__":
    main()
