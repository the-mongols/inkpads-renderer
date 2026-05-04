import json
import math
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

class TacticalRenderer:
    def __init__(self, report_path, output_path="tactical_output.png"):
        self.report_path = Path(report_path)
        self.output_path = Path(output_path)
        
        with open(report_path) as f:
            self.report = json.load(f)
            
        self.meta = self.report["metadata"]
        self.events = self.report["events"]
        self.map_info = self.meta["map"]
        self.space_size = self.map_info["space_size"]
        self.dwell_matrices = self.meta["dwell_matrices"]
        self.my_team = self.meta.get("my_team", 1)
        
        self.CANVAS_SIZE = 2048 
        
        self.colors = {
            "heatmap": (255, 255, 0), # Yellow
            "surgical_trace": (255, 0, 0, 150), # Red dots for friendly dmg
            "grid": (255, 255, 255, 20),
            "background": (10, 15, 25, 255),
            "us": (100, 150, 255, 255),
            "them": (255, 100, 100, 255),
            "shot": (255, 255, 255, 40)
        }
        
        self.unique_enemy_colors = {}
        self.enemy_palette = [
            (255, 100, 100), (255, 150, 50), (255, 200, 50),
            (255, 50, 150), (200, 50, 255), (255, 100, 200),
            (255, 150, 150), (255, 200, 200)
        ]

    def world_to_pixel(self, wx, wz):
        nx = (wx / self.space_size) + 0.5
        ny = (wz / self.space_size) + 0.5
        px = nx * self.CANVAS_SIZE
        py = (1.0 - ny) * self.CANVAS_SIZE
        return int(px), int(py)

    def get_enemy_color(self, sid):
        if sid not in self.unique_enemy_colors:
            idx = len(self.unique_enemy_colors) % len(self.enemy_palette)
            self.unique_enemy_colors[sid] = self.enemy_palette[idx]
        return self.unique_enemy_colors[sid]

    def render(self):
        print(f"Rendering Advanced Forensic Visual: {self.output_path}...")
        canvas = Image.new("RGBA", (self.CANVAS_SIZE, self.CANVAS_SIZE), self.colors["background"])
        
        # Layer 1: Map Assets
        land_path = self.map_info["assets"]["land"]
        if land_path and Path(land_path).exists():
            land = Image.open(land_path).convert("RGBA").resize((self.CANVAS_SIZE, self.CANVAS_SIZE))
            edges = land.filter(ImageFilter.FIND_EDGES)
            edges_data = np.array(edges)
            edges_data[edges_data[:,:,3] > 0] = [255, 255, 255, 30]
            canvas.alpha_composite(Image.fromarray(edges_data, "RGBA"))

        draw = ImageDraw.Draw(canvas)
        
        # Layer 2: Engagement Pips (Shots)
        self.draw_engagement_pips(draw)
        
        # Layer 3: Dwell Heatmap (Enemy = team 2 or not my_team)
        enemy_team = "2" if str(self.my_team) != "2" else "1"
        if enemy_team in self.dwell_matrices:
            self.draw_heatmap(draw, self.dwell_matrices[enemy_team])
        
        # Layer 4: Cap Pie Charts & Contest Dots
        self.draw_caps(draw)
        
        # Layer 5: Surgical Traces (Friendly Damage)
        self.draw_damage_traces(draw)
        
        # Layer 6: First Spots (Icons + Names)
        self.draw_spots(draw)
        
        # Layer 7: Deaths (Red X enemy BB, Blue X friendly BB)
        self.draw_deaths(draw)
        
        # Layer 8: Grid Labels
        self.draw_grid(draw)

        canvas.save(self.output_path)
        print(f"Standardized Forensic narrative complete.")

    def draw_heatmap(self, draw, matrix):
        flat = [v for row in matrix for v in row]
        max_val = max(flat) if flat else 1
        cell_size = self.CANVAS_SIZE / 100
        for gy in range(100):
            for gx in range(100):
                val = matrix[gy][gx]
                if val > 0:
                    alpha = min(255, int((val / max_val) * 160) + 30)
                    draw.rectangle([gx*cell_size+1, (99-gy)*cell_size+1, (gx+1)*cell_size-1, (100-gy)*cell_size-1], 
                                   fill=(*self.colors["heatmap"], alpha))

    def draw_engagement_pips(self, draw):
        for shot in self.events.get("shots", []):
            ox, oz = shot["ox"], shot["oz"]
            if ox is None: continue
            px, py = self.world_to_pixel(ox, oz)
            r = 3
            draw.ellipse([px-r, py-r, px+r, py+r], fill=self.colors["shot"])

    def draw_caps(self, draw):
        for eid, cap in self.events["caps"].items():
            px, py = self.world_to_pixel(cap["wx"], cap["wz"])
            pr = (cap["radius"] / self.space_size) * self.CANVAS_SIZE
            
            # Pie Chart logic
            durations = cap.get("ownership_duration", {})
            total = sum(durations.values())
            if total > 0:
                start_angle = -90
                # Map teams to Us/Them colors
                for team_str, dur in durations.items():
                    if dur > 0:
                        extent = (dur / total) * 360
                        color = self.colors["us"] if int(team_str) == self.my_team else self.colors["them"]
                        # Faded pie
                        pie_color = (*color[:3], 60)
                        draw.pieslice([px-pr, py-pr, px+pr, py+pr], start_angle, start_angle + extent, fill=pie_color, outline=(*color[:3], 150))
                        start_angle += extent
            else:
                draw.ellipse([px-pr, py-pr, px+pr, py+pr], outline=(255, 255, 255, 40), width=4)

            # Label
            label = chr(65 + cap["index"])
            font = self.get_font(100)
            w, h = draw.textbbox((0,0), label, font=font)[2:]
            draw.text((px-w/2, py-h/2), label, fill=(255, 255, 255, 120), font=font)
            
            # Contest Dots
            for contest in cap.get("contests", []):
                cx, cy = self.world_to_pixel(contest["wx"], contest["wz"])
                color = (0, 255, 0, 200) if contest["team"] == self.my_team else (255, 0, 0, 200)
                draw.ellipse([cx-8, cy-8, cx+8, cy+8], fill=color)

    def draw_damage_traces(self, draw):
        for ev in self.events["damage"]:
            px, py = self.world_to_pixel(ev["wx"], ev["wz"])
            draw.ellipse([px-3, py-3, px+3, py+3], fill=self.colors["surgical_trace"])

    def draw_spots(self, draw):
        for spot in self.events["spots"]:
            px, py = self.world_to_pixel(spot["wx"], spot["wz"])
            sid = spot["sid"]
            species = spot.get("species", "Unknown")
            color = self.get_enemy_color(sid)
            
            self.draw_ship_icon(draw, px, py, species, (*color, 255))
            
            # Label: Ship Name + Player Name
            label = f"{spot['ship']}\n({spot['player']})"
            font = self.get_font(36)
            draw.text((px + 35, py - 25), label, fill=(255, 255, 255, 255), font=font, stroke_width=1, stroke_fill=(0,0,0,255))

    def draw_ship_icon(self, draw, px, py, species, color, size=24):
        if species == "Battleship":
            draw.rectangle([px-size, py-size/3, px+size, py+size/3], fill=color, outline=(0,0,0,255))
        elif species == "Cruiser":
            draw.polygon([(px, py-size), (px+size, py), (px, py+size), (px-size, py)], fill=color, outline=(0,0,0,255))
        elif species == "Destroyer":
            draw.polygon([(px, py-size), (px+size, py+size), (px-size, py+size)], fill=color, outline=(0,0,0,255))
        elif species == "AirCarrier":
            draw.rectangle([px-size, py-size, px+size, py+size], fill=color, outline=(0,0,0,255))
        elif species == "Submarine":
            draw.ellipse([px-size, py-size/2, px+size, py+size/2], fill=color, outline=(0,0,0,255))
        else:
            draw.ellipse([px-size, py-size, px+size, py+size], fill=color, outline=(0,0,0,255))

    def draw_deaths(self, draw):
        for death in self.events["deaths"]:
            if death.get("is_bb"):
                px, py = self.world_to_pixel(death["wx"], death["wz"])
                r = 45
                # Enemy = Them color (Red), Friendly = Us color (Blue)
                color = self.colors["us"] if death["team"] == self.my_team else self.colors["them"]
                draw.line([px-r, py-r, px+r, py+r], fill=color, width=14)
                draw.line([px+r, py-r, px-r, py+r], fill=color, width=14)

    def draw_grid(self, draw):
        step = self.CANVAS_SIZE / 10
        font = self.get_font(44)
        for i in range(11):
            draw.line([0, i*step, self.CANVAS_SIZE, i*step], fill=self.colors["grid"], width=2)
            draw.line([i*step, 0, i*step, self.CANVAS_SIZE], fill=self.colors["grid"], width=2)
            if i < 10:
                draw.text((15, i*step + 15), chr(65+i), fill=(255,255,255,80), font=font)
                draw.text((i*step + step/2, 15), str(i+1), fill=(255,255,255,80), font=font)

    def get_font(self, size):
        try:
            return ImageFont.truetype("arial.ttf", size)
        except:
            return ImageFont.load_default()

if __name__ == "__main__":
    renderer = TacticalRenderer("match_report.json")
    renderer.render()
