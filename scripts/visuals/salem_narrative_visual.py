import json
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import os

# Forensic Constants for HD Map "Domination_41_Conquest.jpg"
# Engine Scale: 2330.0 units (-1165 to 1165)
SCALE_RATIO = 760 / 2330.0 
OFFSET_X = 402 
OFFSET_Y = 402

def world_to_pixel(wx, wz):
    px = OFFSET_X + (wx * SCALE_RATIO)
    py = OFFSET_Y - (wz * SCALE_RATIO)
    return px, py

def create_tactical_narrative(data_path, map_path, output_path):
    if not os.path.exists(data_path): return

    with open(data_path, "r") as f:
        data = json.load(f)

    base_map = Image.open(map_path).convert("RGBA")
    draw = ImageDraw.Draw(base_map)
    
    # 1. Cap Markers (A, B, C Teal Circles)
    caps = [
        {"name": "A", "wx": -466.0, "wz": 0.0},
        {"name": "B", "wx": 0.0, "wz": 0.0},
        {"name": "C", "wx": 466.0, "wz": 0.0}
    ]
    
    try:
        cap_font = ImageFont.truetype("arial.ttf", 40)
    except:
        cap_font = ImageFont.load_default()

    for cap in caps:
        px, py = world_to_pixel(cap["wx"], cap["wz"])
        # Teal Circle
        r = 60
        draw.ellipse([px-r, py-r, px+r, py+r], fill=(0, 128, 128, 120), outline=(200, 200, 200, 180), width=2)
        draw.text((px, py), cap["name"], fill=(255, 255, 255, 255), font=cap_font, anchor="mm")

    # 2. Render Heatmap (Faint Yellow Grid)
    heatmap_res = 16 
    heatmap = np.zeros((heatmap_res, heatmap_res))
    for trail in data.get("enemy_trails", []):
        for wx, wz in trail["path"]:
            px, py = world_to_pixel(wx, wz)
            gx = int((px - 22) / (760/heatmap_res))
            gy = int((py - 22) / (760/heatmap_res))
            if 0 <= gx < heatmap_res and 0 <= gy < heatmap_res:
                heatmap[gy, gx] += 1

    if heatmap.max() > 0:
        heatmap = heatmap / heatmap.max()
        cell_size = 760 / heatmap_res
        for y in range(heatmap_res):
            for x in range(heatmap_res):
                alpha = int(heatmap[y, x] * 120)
                if alpha > 10:
                    overlay = Image.new("RGBA", (int(cell_size), int(cell_size)), (255, 255, 0, alpha))
                    base_map.paste(overlay, (int(22 + x * cell_size), int(22 + y * cell_size)), overlay)

    # 3. Enemy Smoke Screens (White Dotted Paths)
    for smoke in data.get("enemy_smoke_events", []):
        px, py = world_to_pixel(smoke["wx"], smoke["wz"])
        # White dots for smoke trail
        draw.ellipse([px-3, py-3, px+3, py+3], fill=(255, 255, 255, 255))

    # 4. Spotting Events (White Diamonds + Label)
    try:
        font = ImageFont.truetype("arial.ttf", 14)
    except:
        font = ImageFont.load_default()

    for event in data.get("first_spot_events", []):
        px, py = world_to_pixel(event["wx"], event["wz"])
        # Diamond Marker
        s = 5
        draw.polygon([px, py-s, px+s, py, px, py+s, px-s, py], fill=(255, 255, 255), outline=(0,0,0))
        draw.text((px + 10, py), event.get("ship", "Unknown"), fill=(255, 255, 255), font=font, anchor="lm")

    # Save Final Narrative
    base_map.convert("RGB").save(output_path)
    print(f"Tactical Narrative v36 Look-and-Feel restored at: {output_path}")

if __name__ == "__main__":
    create_tactical_narrative("salem_shredded_data.json", "maps/Domination_41_Conquest.jpg", "salem_tactical_narrative_v44.png")
