import json
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Configuration
REPLAY_PATH = r"C:\Games\World_of_Warships\replays\20260428_113338_PASC710-Salem_25_sea_hope.wowsreplay"
REPLAYSHARK_EXE = r"target\release\replayshark.exe"
GAME_DIR = r"C:\Games\World_of_Warships"

# Map Metadata (Sea of Fortune)
SPACE_SIZE = 1600 # 1600 BigWorld Units = 48,000 meters
MAP_SIZE_PX = 760  # Native game minimap size

# Asset Paths
ASSETS_DIR = Path("inkpads-bot/assets/maps/25_sea_hope/spaces/25_sea_hope")
WATER_IMG = ASSETS_DIR / "minimap_water.png"
LAND_IMG = ASSETS_DIR / "minimap.png"
OUTPUT_IMG = Path("salem_sabermetrics.png")

def world_to_pixel(world_x, world_z):
    """Converts world coordinates (meters) to image pixel coordinates."""
    # Scale: pixels per meter
    scale = MAP_SIZE_PX / SPACE_SIZE
    half = MAP_SIZE_PX / 2
    
    # Math from Rust: (pos.x * scale + half)
    # Z is typically inverted in minimap display
    px = (world_x * scale) + half
    py = ((-world_z) * scale) + half
    
    return int(px), int(py)

def main():
    print("--- InkPads Visual Sabermetrics Engine ---")
    
    # 1. Create Base Map
    print("Compositing map assets...")
    water = Image.open(WATER_IMG).convert("RGBA")
    land = Image.open(LAND_IMG).convert("RGBA")
    base_map = Image.alpha_composite(water, land)
    
    draw = ImageDraw.Draw(base_map)
    
    # 2. Extract Data
    print(f"Extracting telemetry for The_Mongols (ID: 293987)...")
    cmd = [REPLAYSHARK_EXE, "-g", GAME_DIR, "dump", REPLAY_PATH]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)
    
    points = []
    # (pixel_x, pixel_y, duration)
    telemetry_data = []
    
    target_pid = 293987
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
        print("Error: No telemetry found.")
        return

    # 3. High-Fidelity Rendering (4x Supersampling)
    print("Generating High-Fidelity Tactical Visuals (4x SSAA)...")
    RENDER_SCALE = 4
    HI_RES = MAP_SIZE_PX * RENDER_SCALE
    
    # Create Hi-Res layers
    hi_res_heat = Image.new("RGBA", (HI_RES, HI_RES), (0,0,0,0))
    hi_res_path = Image.new("RGBA", (HI_RES, HI_RES), (0,0,0,0))
    heat_draw = ImageDraw.Draw(hi_res_heat)
    path_draw = ImageDraw.Draw(hi_res_path)
    
    # Layer 1: Heat Blobs (Additive Neon Orange)
    for x, y, duration in telemetry_data:
        # Scale coordinates to Hi-Res
        hx, hy = x * RENDER_SCALE, y * RENDER_SCALE
        r = 20 * RENDER_SCALE # Broad, smooth blobs
        # Higher alpha for visibility
        a = min(180, 50 + int(duration * 200))
        if a > 0:
            heat_draw.ellipse([hx-r, hy-r, hx+r, hy+r], fill=(255, 80, 0, a))
            
    # Layer 2: Glowing Cyan Path
    if len(points) > 1:
        # Scale points to Hi-Res
        scaled_points = [(p[0] * RENDER_SCALE, p[1] * RENDER_SCALE) for p in points]
        # Dark outer glow
        path_draw.line(scaled_points, fill=(0, 0, 0, 200), width=10 * RENDER_SCALE)
        # Main Cyan line
        path_draw.line(scaled_points, fill=(0, 255, 255, 255), width=3 * RENDER_SCALE)

    # 4. Composite & Downscale
    print("Compositing and filtering...")
    # Initial Blur on Hi-Res for smoothness
    from PIL import ImageFilter
    hi_res_heat = hi_res_heat.filter(ImageFilter.GaussianBlur(radius=8 * RENDER_SCALE))
    
    # Composite onto a scaled version of the base map
    final_base = base_map.resize((HI_RES, HI_RES), Image.Resampling.LANCZOS)
    final_base.paste(hi_res_heat, (0, 0), hi_res_heat)
    final_base.paste(hi_res_path, (0, 0), hi_res_path)
    
    # Downscale to native size for crispness
    output_img = final_base.resize((MAP_SIZE_PX, MAP_SIZE_PX), Image.Resampling.LANCZOS)
    
    # Final sharpening pass
    output_img = output_img.filter(ImageFilter.SHARPEN)
    
    # 5. Add Grid Overlay (Native Resolution for absolute sharpness)
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
