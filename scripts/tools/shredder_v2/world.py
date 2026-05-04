from pathlib import Path
import json
import math

class WorldState:
    """
    Manages the 'Source of Truth' for the match.
    Tracks roster, map calibration, and entity mappings.
    """
    def __init__(self):
        self.player_name = None
        self.my_team = -1
        self.map_name = None
        self.space_size = 0
        
        # Identity Mappings
        self.roster = {}  # sid -> info
        self.name_to_sid = {} # player_name -> sid
        self.ship_mapping = {}
        
    def load_ship_mapping(self, path="ship_mapping.json"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.ship_mapping = json.load(f)
        except:
            print("Warning: Could not load ship_mapping.json")

    def update_roster(self, sid, name, ship_id=None, team=None):
        # If we already have this player by name but didn't have their SID yet
        if not sid and name in self.name_to_sid:
            sid = self.name_to_sid[name]
        
        if sid and name:
            self.name_to_sid[name] = sid

        if sid not in self.roster:
            self.roster[sid] = {
                "sid": sid,
                "player_name": name,
                "name": "Unknown", # Ship Type Name
                "species": "Unknown",
                "team": team,
                "ship_id": ship_id,
                "last_pos": (0, 0)
            }
        
        entry = self.roster[sid]
        if ship_id:
            entry["ship_id"] = ship_id
            if self.ship_mapping and str(ship_id) in self.ship_mapping:
                mapping = self.ship_mapping[str(ship_id)]
                entry["name"] = mapping["name"]
                entry["species"] = mapping["species"]
                
        if team is not None:
            entry["team"] = team

    def get_ship_by_sid(self, sid):
        return self.roster.get(sid)

    def get_roster(self):
        # Returns sid-keyed roster but ensures 'name' field is ship type
        return self.roster
