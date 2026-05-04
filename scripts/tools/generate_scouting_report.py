from shredder_v2 import ForensicEngine, ForensicAnalyst, ScoutingRenderer
from map_resolver import MapResolver
import os
from pathlib import Path

def generate_report(audit_path):
    print(f"--- Generating Scouting Report from {audit_path} ---")
    
    # 1. Analyst Phase
    analyst = ForensicAnalyst(audit_path)
    enemy_team = analyst.get_enemy_team_id()
    
    # Extract "Opening Gambit" anchors (0-7 mins)
    raw_anchors = analyst.extract_anchor_points(enemy_team, time_range=(0, 420))
    
    # Normalize (ensure target clan is at South)
    normalized_anchors = analyst.normalize_for_scouting(raw_anchors, enemy_team)
    
    # 2. Visualization Phase
    # We'll use a dummy MapResolver for the demo image background
    resolver = MapResolver(game_dir="", unpacker_exe="") 
    renderer = ScoutingRenderer(resolver)
    
    metadata = {
        "target_clan": "SCOUTED_CLAN", # In real use, we'd look this up
        "map_name": analyst.metadata.get("map_name", "Unknown Map"),
        "phase": "Opening Gambit (0-7:00)",
        "caps": analyst.telemetry.get("caps", {})
    }
    
    output_file = "scouting_report_demo.png"
    renderer.render_scouting_report(
        map_name=metadata["map_name"],
        bounds=analyst.metadata.get("bounds", {}),
        clusters=normalized_anchors,
        metadata=metadata,
        output_path=output_file
    )
    
    print(f"Success! Scouting report generated: {output_file}")
    print(f"Identified {len(normalized_anchors)} Strategic Anchors for the target clan.")

if __name__ == "__main__":
    if os.path.exists("forensic_audit_v2.json"):
        generate_report("forensic_audit_v2.json")
    else:
        print("Error: forensic_audit_v2.json not found. Run test_v2_engine.py first.")
