import xml.etree.ElementTree as ET
from pathlib import Path
import json
import subprocess

class MapResolver:
    def __init__(self, assets_root="assets/maps", game_dir=None, unpacker_exe=None):
        self.assets_root = Path(assets_root)
        self.game_dir = game_dir
        self.unpacker_exe = unpacker_exe

    def find_map_dir(self, map_name):
        # map_name from replay is often "spaces/41_Conquest" or just "41_Conquest"
        clean_name = map_name.split("/")[-1]
        
        # Search for directory ending in clean_name
        self.assets_root.mkdir(parents=True, exist_ok=True)
        for p in self.assets_root.iterdir():
            if p.is_dir() and clean_name in p.name:
                return p
        
        # If not found and we have game_dir/unpacker, try to extract it
        if self.game_dir and self.unpacker_exe:
            print(f"Map {map_name} not found locally. Attempting to extract...")
            try:
                target_dir = self.assets_root / clean_name
                target_dir.mkdir(parents=True, exist_ok=True)
                
                # Extract from game archives
                # Paths in archives start with /spaces/
                space_path = f"/spaces/{clean_name}"
                cmd = [
                    self.unpacker_exe, "-g", self.game_dir, "extract", 
                    "--out-dir", "temp_unpack", f"{space_path}/minimap*", f"{space_path}/space.settings"
                ]
                subprocess.run(cmd, check=True)
                
                # Move extracted files to target_dir
                extracted_path = Path("temp_unpack") / "spaces" / clean_name
                if extracted_path.exists():
                    for f in extracted_path.iterdir():
                        dest = target_dir / f.name
                        if dest.exists(): dest.unlink()
                        f.rename(dest)
                    return target_dir
            except Exception as e:
                print(f"Failed to extract map {map_name}: {e}")
        
        return None

    def resolve(self, map_name):
        map_dir = self.find_map_dir(map_name)
        if not map_dir:
            print(f"Warning: Map directory for {map_name} not found.")
            return self.get_default_metadata()

        # Find space.settings (could be nested)
        settings_path = next(map_dir.rglob("space.settings"), None)
        if not settings_path:
            print(f"Warning: space.settings not found in {map_dir}")
            return self.get_default_metadata()

        try:
            tree = ET.parse(settings_path)
            root = tree.getroot()
            bounds = root.find("bounds")
            
            min_x = int(bounds.get("minX"))
            max_x = int(bounds.get("maxX"))
            min_y = int(bounds.get("minY"))
            max_y = int(bounds.get("maxY"))

            # Each chunk is 600 BigWorld units (meters)
            width_units = (max_x - min_x + 1) * 600
            height_units = (max_y - min_y + 1) * 600
            
            # Maps are square, use the larger dimension as the baseline
            space_size = max(width_units, height_units)

            # Find minimap asset
            minimap_path = next(map_dir.rglob("minimap.png"), None)
            water_path = next(map_dir.rglob("minimap_water.png"), None)

            return {
                "map_name": map_name,
                "space_size": float(space_size),
                "bounds": {
                    "min_x": min_x, "max_x": max_x,
                    "min_y": min_y, "max_y": max_y
                },
                "assets": {
                    "land": str(minimap_path) if minimap_path else None,
                    "water": str(water_path) if water_path else None
                }
            }
        except Exception as e:
            print(f"Error parsing space.settings: {e}")
            return self.get_default_metadata()

    def get_default_metadata(self):
        # Fallback for unknown maps
        return {
            "map_name": "Unknown",
            "space_size": 12000.0, # Typical 20x20 map
            "bounds": {"min_x": -10, "max_x": 9, "min_y": -10, "max_y": 9},
            "assets": {"land": None, "water": None}
        }

if __name__ == "__main__":
    resolver = MapResolver()
    # Test with Archipelago
    meta = resolver.resolve("04_Archipelago")
    print(json.dumps(meta, indent=4))
    
    # Test with Trident
    meta = resolver.resolve("41_Conquest")
    print(json.dumps(meta, indent=4))
