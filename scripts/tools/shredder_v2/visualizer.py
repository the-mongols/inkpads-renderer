import os
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pathlib import Path

class ScoutingRenderer:
    """
    Renders high-resolution tactical scouting heatmaps.
    """
    def __init__(self, map_resolver, output_size=(2048, 2048)):
        self.resolver = map_resolver
        self.output_size = output_size
        self.font_size = output_size[0] // 40
        
        # Try to load a font
        try:
            self.font = ImageFont.truetype("arial.ttf", self.font_size)
        except:
            self.font = ImageFont.load_default()

    def world_to_pixel(self, wx, wz, space_size):
        """
        PORTED FROM crates/minimap-renderer/src/map_data.rs
        Definitive coordinate transformation used by the video renderer.
        """
        NATIVE_SIZE = 760.0
        output_size = float(self.output_size[0])
        
        scale = NATIVE_SIZE / float(space_size)
        half = NATIVE_SIZE / 2.0
        rescale = output_size / NATIVE_SIZE
        
        px = ((wx * scale) + half) * rescale
        pz = ((-wz * scale) + half) * rescale
        
        return px, pz

    def render_scouting_report(self, map_name, bounds, clusters, metadata, output_path):
        """
        Creates the final Scouting Report image.
        """
        # 1. Load Background
        bg = self._load_map_background(map_name)
        draw = ImageDraw.Draw(bg, "RGBA")
        
        # 2. Draw Grid
        self._draw_grid(draw)
        
        # 3. Draw Objectives (Caps)
        self._draw_caps(draw, bounds, metadata.get("caps", {}))
        
        # 4. Draw Heat Blobs
        self._draw_heat(bg, draw, bounds, clusters)
        
        # 5. Draw Header/Metadata
        self._draw_metadata(draw, metadata)
        
        # 6. Save
        bg.save(output_path, "PNG")
        return output_path

    def _load_map_background(self, map_name):
        """Finds and loads the raw game minimap or the HD version."""
        # Check for extracted raw asset first (Trident = 41_Conquest)
        raw_path = Path("temp_unpack") / "spaces" / "41_Conquest" / "minimap.png"
        
        if raw_path.exists():
            try:
                img = Image.open(raw_path).convert("RGBA")
                img = img.resize(self.output_size, Image.LANCZOS)
                # Darken the background slightly to make heat blobs pop
                enhancer = Image.new("RGBA", self.output_size, (0, 0, 0, 80))
                img = Image.alpha_composite(img, enhancer)
                return img
            except Exception as e:
                print(f"Failed to load raw minimap: {e}")

        # Fallback to dark tactical blue
        return Image.new("RGBA", self.output_size, (5, 10, 20, 255))

    def _draw_grid(self, draw):
        """Draws the grid with WoWs-standard labels: 1-10 on X, A-J on Y."""
        w, h = self.output_size
        line_color = (255, 255, 255, 25) 
        text_color = (255, 255, 255, 120)
        
        for i in range(11):
            x = (w / 10) * i
            y = (h / 10) * i
            draw.line([(x, 0), (x, h)], fill=line_color, width=1)
            draw.line([(0, y), (w, y)], fill=line_color, width=1)
            
            if i < 10:
                # Top Labels (1-10) - Traditional X-axis
                label = str(i + 1)
                draw.text((x + (w/20) - 10, 10), label, font=self.font, fill=text_color)
                # Left Labels (A-J) - Traditional Y-axis
                label = chr(65 + i)
                draw.text((10, y + (h/20) - 10), label, font=self.font, fill=text_color)

    def _draw_caps(self, draw, bounds, caps):
        """Draws prominent capture zones with corrected scaling."""
        sw, sh = self.output_size
        size = bounds.get("space_size", 10800)
        
        # FACT: InteractiveZone coordinates in replayshark are often scaled 
        # to a 1000-unit grid (-500 to 500). We need to project these to World Meters.
        # For Trident (10800m), the factor is roughly 10.8 / 1.0 (if -500..500)
        # However, the native minimap grid is 760. 
        # Let's use the verified scaling: World = Normalized * (Space_Size / 1000.0)
        
        for sid, cap in caps.items():
            # Correcting the 'Clustered' coordinates
            # Most caps in replayshark are relative to a 1000m 'Base' or normalized
            wx = cap["wx"] * (size / 1000.0) 
            wz = cap["wz"] * (size / 1000.0)
            
            px, pz = self.world_to_pixel(wx, wz, size)
            
            # Use a more tactical radius (Trident caps are usually ~400-600m)
            # The '110' radius in the packet is also normalized.
            radius_world = cap["radius"] * (size / 1000.0)
            radius_px = (radius_world / size) * sw
            
            # Thick, prominent white outline
            bbox = [px - radius_px, pz - radius_px, px + radius_px, pz + radius_px]
            draw.ellipse(bbox, outline=(255, 255, 255, 180), width=3)
            
            # Label
            label = chr(65 + cap.get("index", 0))
            draw.text((px - 15, pz - 15), label, font=self.font, fill=(255, 255, 255, 220))

    def _draw_heat(self, bg, draw, bounds, clusters):
        """Draws engagement pockets with edge-aware, stacked labels."""
        sw, sh = self.output_size
        size = bounds.get("space_size", 10800)
        
        # Track used slots (x_bin, y_bin) to stack labels
        # We'll use a simple grid to find collisions
        label_slots = {}
        
        for c in sorted(clusters, key=lambda x: x["intensity"]):
            px, pz = self.world_to_pixel(c["wx"], c["wz"], size)
            
            # Species Colors
            species = c.get("species", "Unknown")
            if species == "Cruiser": color = (255, 60, 60)
            elif species == "Battleship": color = (255, 180, 0)
            elif species == "Destroyer": color = (0, 240, 255)
            else: color = (180, 180, 180)
            
            base_radius = sw // 120 
            intensity_factor = min(3.5, 1.0 + (c["intensity"] / 1000))
            radius = base_radius * intensity_factor
            
            # Glow layers
            for layer in range(4, 0, -1):
                r = radius * (layer / 4)
                alpha = int(140 * (1 - (layer/5))) 
                fill_color = color + (alpha,)
                draw.ellipse([px - r, pz - r, px + r, pz + r], fill=fill_color)
            
            # Centroid dot
            draw.ellipse([px - 3, pz - 3, px + 3, pz + 3], fill=(255, 255, 255, 255))
            
            # Edge-Aware Labels
            ship_name = c.get("name", "Unknown Ship")
            
            # If we are in the last 20% of the map, draw label to the left
            is_right_edge = px > (sw * 0.8)
            
            if is_right_edge:
                label_x = px - radius - 120 # Move to left of blob
            else:
                label_x = px + radius + 10 # Standard right of blob
            
            # Stacking logic
            x_bin = int(label_x / 100)
            y_bin = int(pz / 30)
            
            slot_key = (x_bin, y_bin)
            while slot_key in label_slots:
                y_bin += 1 # Nudge down
                slot_key = (x_bin, y_bin)
            
            label_slots[slot_key] = ship_name
            label_y = y_bin * 30
            
            # Draw label with shadow
            shadow_offset = 1
            draw.text((label_x + shadow_offset, label_y + shadow_offset), ship_name, font=self.font, fill=(0, 0, 0, 200))
            draw.text((label_x, label_y), ship_name, font=self.font, fill=(255, 255, 255, 255))

    def _draw_metadata(self, draw, metadata):
        """Draws the tactical legend with proper spacing."""
        w, h = self.output_size
        text_color = (255, 255, 255, 220)
        warning_color = (255, 80, 80, 255)
        
        # Use a dynamic line height based on font size
        line_height = int(self.font_size * 1.3)
        margin = 30
        
        # Start from the bottom and move up
        current_y = h - margin - (line_height * 5)
        
        # Main Header
        draw.text((margin, current_y), f"SCOUTING REPORT: {metadata.get('target_clan', 'UNKNOWN')}", font=self.font, fill=text_color)
        current_y += line_height
        
        draw.text((margin, current_y), f"Map: {metadata.get('map_name', 'Unknown')}", font=self.font, fill=text_color)
        current_y += line_height
        
        draw.text((margin, current_y), f"Phase: {metadata.get('phase', 'Unknown')}", font=self.font, fill=text_color)
        current_y += line_height
        
        # Ghost Ships
        ghosts = metadata.get("ghost_ships", [])
        if ghosts:
            draw.text((margin, current_y), "GHOST ALERT (STEALTH):", font=self.font, fill=warning_color)
            current_y += line_height
            ghost_text = ", ".join(ghosts)
            draw.text((margin + 20, current_y), f"> {ghost_text}", font=self.font, fill=warning_color)
        else:
            draw.text((margin, current_y), "Oriented: Target Team at South", font=self.font, fill=text_color)
