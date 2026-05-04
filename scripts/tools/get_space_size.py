import xml.etree.ElementTree as ET

def get_space_size(path):
    tree = ET.parse(path)
    root = tree.getroot()
    bounds = root.find("bounds")
    min_x = int(bounds.get("minX"))
    max_x = int(bounds.get("maxX"))
    min_y = int(bounds.get("minY"))
    max_y = int(bounds.get("maxY"))
    
    width_units = (max_x - min_x + 1) * 600
    height_units = (max_y - min_y + 1) * 600
    return max(width_units, height_units)

print(f"Space Size for 41_Conquest: {get_space_size('temp_unpack/spaces/41_Conquest/space.settings')}")
