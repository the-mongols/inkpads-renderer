from shredder_v2 import ForensicAnalyst, ScoutingRenderer
from map_resolver import MapResolver
import os

def clean_ship_name(raw_name):
    """Standardizes ship names across the engine."""
    parts = raw_name.split("_")
    if len(parts) >= 2:
        if parts[-1].isdigit() and len(parts) >= 3:
            clean = parts[-2]
        else:
            clean = parts[1] if len(parts[1]) > 3 else parts[-1]
    else:
        clean = raw_name
        
    if "Baltimore" in raw_name: clean = "Baltimore"
    if "Turgut" in raw_name: clean = "Turgut Reis"
    if "Cossack" in raw_name: clean = "Cossack B"
    if "Shigure" in raw_name: clean = "Shigure"
    if "Cataluna" in raw_name: clean = "Cataluna"
    if "Bayard" in raw_name: clean = "Bayard"
    if "Cherbourg" in raw_name: clean = "Cherbourg"
    
    return clean

def generate_final_report(audit_path):
    print(f"--- Finalizing Labeled Scouting Report for {audit_path} ---")
    
    analyst = ForensicAnalyst(audit_path)
    enemy_team_id = analyst.get_enemy_team_id()
    
    # 1. Extract and Clean Anchors
    raw_anchors = analyst.extract_anchor_points(enemy_team_id, time_range=(0, 420))
    
    consolidated = {}
    for a in raw_anchors:
        a["name"] = clean_ship_name(a.get("name", "Unknown"))
        ship_id = a["name"]
        if ship_id not in consolidated or a["intensity"] > consolidated[ship_id]["intensity"]:
            consolidated[ship_id] = a
    
    final_anchors = list(consolidated.values())
    
    # 2. Identify Ghosts (using the SAME cleaning logic)
    spotted_names = {a["name"] for a in final_anchors}
    ghost_ships = []
    
    for info in analyst.roster.values():
        if info.get("team") == enemy_team_id:
            raw_ship_name = info.get("name", "Unknown")
            if raw_ship_name == "Unknown": continue
            
            clean_name = clean_ship_name(raw_ship_name)
            if clean_name not in spotted_names:
                ghost_ships.append(clean_name)

    # Remove duplicates from ghosts
    ghost_ships = list(set(ghost_ships))

    # 3. Render
    normalized_anchors = analyst.normalize_for_scouting(final_anchors, enemy_team_id)
    resolver = MapResolver(game_dir="", unpacker_exe="") 
    renderer = ScoutingRenderer(resolver)
    
    metadata = {
        "target_clan": "HHGA",
        "map_name": "Trident (41_Conquest)",
        "phase": "Opening Gambit (0-7:00)",
        "caps": analyst.telemetry.get("caps", {}),
        "ghost_ships": ghost_ships
    }
    
    renderer.render_scouting_report(
        map_name="41_Conquest",
        bounds=analyst.metadata.get("bounds", {}),
        clusters=normalized_anchors,
        metadata=metadata,
        output_path="scouting_report_HHGA_Trident.png"
    )
    
    print(f"Success! Final scouting report generated. Ghosts: {ghost_ships}")

if __name__ == "__main__":
    generate_final_report("forensic_audit_v2.json")
