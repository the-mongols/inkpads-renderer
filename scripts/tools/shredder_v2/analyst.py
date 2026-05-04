import json
import math
from pathlib import Path

class ForensicAnalyst:
    """
    Consumes forensic_audit_v2.json to extract high-level tactical intelligence.
    Focuses on Enemy Occupancy and Anchor Points for scouting.
    """
    def __init__(self, audit_path):
        with open(audit_path, 'r') as f:
            self.data = json.load(f)
        
        self.metadata = self.data.get("metadata", {})
        self.telemetry = self.data.get("telemetry", {})
        self.roster = self.metadata.get("roster", {})
        
    def get_enemy_team_id(self, my_team_id=None):
        """Identify which team is the 'Enemy' relative to the recording player."""
        if my_team_id is None:
            # We know the player is 'The_Mongols'
            player_name = self.metadata.get("player")
            for sid, info in self.roster.items():
                if info.get("player_name") == player_name:
                    my_team_id = info.get("team")
                    break
        
        # All teams in match
        teams = set(info.get("team") for info in self.roster.values() if info.get("team") is not None)
        # Exclude our own team
        enemies = [t for t in teams if t != my_team_id]
        return enemies[0] if enemies else None

    def extract_anchor_points(self, team_id, time_range=(0, 420)):
        """
        Finds 'Occupancy Pockets' where ships dwell/shimmy.
        Uses loosened logic to ensure all ship species (including DDs) are captured.
        """
        all_pockets = []
        trails = self.telemetry.get("trails", {})
        
        for sid, points in trails.items():
            # Find ship info
            ship_info = next((info for info in self.roster.values() if str(info.get("sid")) == str(sid)), None)
            if not ship_info or ship_info.get("team") != team_id:
                continue

            valid_points = [p for p in points if time_range[0] <= p["t"] <= time_range[1]]
            if not valid_points: continue

            # Dynamic constraints for 'Scouting Realism'
            # DDs shimmy more and are spotted less.
            species = ship_info.get("species", "Unknown")
            ship_point_count = len(valid_points)
            
            cluster_radius = 1200 if species == "Destroyer" else 800
            
            # If a DD was barely spotted, we take whatever we can get
            if species == "Destroyer" and ship_point_count < 50:
                dwell_threshold = 10 # Very low threshold for stealthy DDs
            elif species == "Destroyer":
                dwell_threshold = 30
            else:
                dwell_threshold = 50
            
            ship_pockets = []
            for p in valid_points:
                found = False
                for pocket in ship_pockets:
                    dist = math.sqrt((p["x"] - pocket["wx"])**2 + (p["z"] - pocket["wz"])**2)
                    if dist < cluster_radius:
                        pocket["wx"] = (pocket["wx"] * pocket["count"] + p["x"]) / (pocket["count"] + 1)
                        pocket["wz"] = (pocket["wz"] * pocket["count"] + p["z"]) / (pocket["count"] + 1)
                        pocket["count"] += 1
                        found = True
                        break
                if not found:
                    ship_pockets.append({"wx": p["x"], "wz": p["z"], "count": 1})
            
            # Convert ship pockets to anchors
            for pocket in ship_pockets:
                if pocket["count"] >= dwell_threshold:
                    all_pockets.append({
                        "wx": pocket["wx"],
                        "wz": pocket["wz"],
                        "intensity": pocket["count"] * 10, # Intensity multiplier
                        "species": species,
                        "name": ship_info["name"]
                    })
        
        return all_pockets

    def normalize_for_scouting(self, clusters, team_id):
        """
        Normalizes coordinates so the target team always appears as if 
        starting from the 'Bottom' (South) of the map.
        """
        # Determine spawn orientation
        spawn_z = 0
        count = 0
        for sid, points in self.telemetry.get("trails", {}).items():
            ship_info = next((info for info in self.roster.values() if str(info.get("sid")) == str(sid)), None)
            if ship_info and ship_info.get("team") == team_id and points:
                spawn_z += points[0]["z"]
                count += 1
        
        if count == 0: return clusters
        should_flip = (spawn_z / count) > 0 # North spawn
        
        if not should_flip: return clusters

        normalized = []
        for c in clusters:
            nc = c.copy()
            nc["wx"] = -c["wx"]
            nc["wz"] = -c["wz"]
            normalized.append(nc)
        return normalized
