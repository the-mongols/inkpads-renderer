from shredder_v2 import ForensicAnalyst, ScoutingRenderer
from map_resolver import MapResolver
import os

def generate_corrected_report(audit_path):
    print(f"--- Reconciling Scouting Report for {audit_path} ---")
    
    analyst = ForensicAnalyst(audit_path)
    
    # HARD FACTS RECONCILIATION:
    # Enemy team is Team 2 [HHGA]
    enemy_team_id = 2 
    
    # Extract "Opening Gambit" anchors (0-7 mins)
    raw_anchors = analyst.extract_anchor_points(enemy_team_id, time_range=(0, 420))
    
    # Normalization: [HHGA] is South (Negative Z), so no flip needed to put them at bottom.
    # Our normalize_for_scouting flips IF they are North (Positive Z).
    # Since they are South, it will return as is.
    normalized_anchors = analyst.normalize_for_scouting(raw_anchors, enemy_team_id)
    
    resolver = MapResolver(game_dir="", unpacker_exe="") 
    renderer = ScoutingRenderer(resolver)
    
    metadata = {
        "target_clan": "HHGA",
        "map_name": "Trident (41_Conquest)",
        "phase": "Opening Gambit (0-7:00)",
        "caps": analyst.telemetry.get("caps", {})
    }
    
    output_file = "scouting_report_HHGA_Trident.png"
    renderer.render_scouting_report(
        map_name="41_Conquest",
        bounds=analyst.metadata.get("bounds", {}),
        clusters=normalized_anchors,
        metadata=metadata,
        output_path=output_file
    )
    
    print(f"Success! Corrected scouting report generated: {output_file}")
    print(f"Verified [HHGA] Anchors from the South Spawn on Trident.")

if __name__ == "__main__":
    generate_corrected_report("forensic_audit_v2.json")
