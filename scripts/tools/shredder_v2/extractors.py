import math

class BaseExtractor:
    def __init__(self, world):
        self.world = world
        self.data = {}

    def handle(self, packet_type, data, clock):
        pass

    def finalize(self):
        return self.data

class RosterExtractor(BaseExtractor):
    """
    Handles identity resolution and roster population.
    """
    def handle(self, packet_type, data, clock):
        if packet_type == "header":
            self.world.player_name = data.get("playerName")
            for v in data.get("vehicles", []):
                self.world.update_roster(
                    sid=None, # Header doesn't have SID yet
                    name=v.get("name"),
                    ship_id=v.get("shipId"),
                    team=v.get("relation")
                )
                if v.get("name") == self.world.player_name:
                    self.world.my_team = v.get("relation")
        
        elif packet_type == "OnArenaStateReceived":
            states = data.get("player_states", [])
            for s in states:
                details = s.get("raw_with_names", {})
                name = details.get("name")
                sid = details.get("shipId")
                if name and sid:
                    self.world.update_roster(
                        sid=sid,
                        name=name,
                        ship_id=details.get("shipParamsId"),
                        team=details.get("teamId")
                    )

class MovementExtractor(BaseExtractor):
    """
    Handles pathing and dwell time calculations.
    """
    def __init__(self, world):
        super().__init__(world)
        self.data = {
            "dwell_matrices": {0: [[0 for _ in range(100)] for _ in range(100)], 
                               1: [[0 for _ in range(100)] for _ in range(100)],
                               2: [[0 for _ in range(100)] for _ in range(100)]},
            "trails": {} # sid -> list of (t, wx, wz)
        }

    def handle(self, packet_type, data, clock):
        if packet_type == "MinimapUpdate":
            for up in data.get("updates", []):
                sid = up["entity_id"]
                nx, ny = up["position"]["x"], up["position"]["y"]
                
                ship = self.world.get_ship_by_sid(sid)
                if not ship: continue

                # Auto-Calibration Trigger
                if not self.world.is_calibrated and ship["name"] == self.world.player_name:
                    # We need world coords to calibrate. 
                    # Usually provided by EntityCreate or CellPlayerCreate
                    pass 

                if self.world.is_calibrated:
                    wx = (nx - 0.5) * self.world.space_size
                    wz = (ny - 0.5) * self.world.space_size
                    ship["last_pos"] = (wx, wz)
                    
                    # Dwell Matrix (Heatmap)
                    gx, gy = int(nx * 100), int(ny * 100)
                    if 0 <= gx < 100 and 0 <= gy < 100:
                        self.data["dwell_matrices"][ship["team"]][gy][gx] += 1
                    
                    # Store trails for interpolation
                    if sid not in self.data["trails"]: self.data["trails"][sid] = []
                    self.data["trails"][sid].append({"t": clock, "x": wx, "z": wz})

class CombatExtractor(BaseExtractor):
    """
    Handles damage events, shots, and ship destructions.
    """
    def __init__(self, world):
        super().__init__(world)
        self.data = {
            "shots": [],
            "damage": [],
            "deaths": []
        }
        self.health_history = {} # sid -> last_hp

    def handle(self, packet_type, data, clock):
        if packet_type == "ArtilleryShots":
            for salvo in data.get("salvos", []):
                sid = salvo.get("owner_id")
                ship = self.world.get_ship_by_sid(sid)
                for s in salvo.get("shots", []):
                    self.data["shots"].append({
                        "t": clock, "sid": sid,
                        "p": ship["name"] if ship else "Unknown",
                        "ox": s.get("pos", {}).get("x"),
                        "oz": s.get("pos", {}).get("z")
                    })
        
        elif packet_type == "DamageReceived":
            victim_sid = data.get("victim")
            ship = self.world.get_ship_by_sid(victim_sid)
            if ship:
                wx, wz = ship["last_pos"]
                for agg in data.get("aggressors", []):
                    agg_sid = agg.get("aggressor")
                    self.data["damage"].append({
                        "t": clock, "victim": victim_sid, "aggressor": agg_sid,
                        "wx": wx, "wz": wz, "dmg": agg.get("damage", 0)
                    })

        elif packet_type == "ShipDestroyed":
            victim_sid = data.get("victim")
            killer_sid = data.get("killer")
            ship = self.world.get_ship_by_sid(victim_sid)
            if ship:
                wx, wz = ship["last_pos"]
                self.data["deaths"].append({
                    "t": clock, "sid": victim_sid, "killer": killer_sid,
                    "p": ship["name"], "wx": wx, "wz": wz,
                    "species": ship["species"], "team": ship["team"]
                })

class ObjectiveExtractor(BaseExtractor):
    """
    Handles capture zone states and ownership progress.
    """
    def __init__(self, world):
        super().__init__(world)
        self.data = {
            "caps": {} # sid -> info
        }
        self.cap_sids = set()

    def handle(self, packet_type, data, clock):
        if packet_type == "EntityCreate":
            if data.get("entity_type") == "InteractiveZone":
                props = data.get("props", {})
                sid = data["entity_id"]
                if "radius" in props:
                    self.cap_sids.add(sid)
                    self.data["caps"][sid] = {
                        "index": len(self.data["caps"]),
                        "wx": data["position"]["x"], "wz": data["position"]["z"],
                        "radius": props["radius"],
                        "owner": -1, "progress": 0, "invader": -1,
                        "contests": [], "ownership_duration": {0: 0, 1: 0, 2: 0},
                        "last_owner_change": 0
                    }

        elif packet_type == "PropertyUpdate" and data.get("entity_id") in self.cap_sids:
            sid = data["entity_id"]
            prop = data.get("property")
            cap = self.data["caps"][sid]
            
            if prop == "teamId":
                new_team = data.get("value", -1)
                if cap["owner"] != -1:
                    cap["ownership_duration"][cap["owner"]] += (clock - cap["last_owner_change"])
                cap["owner"] = new_team
                cap["last_owner_change"] = clock
            
            elif prop == "componentsState":
                cmd = data.get("update_cmd", {})
                action = cmd.get("action", {})
                if "SetKey" in action:
                    key = action["SetKey"].get("key")
                    val = action["SetKey"].get("value")
                    if key == "progress":
                        cap["progress"] = val
                        if cap["invader"] != -1 and val > 0:
                            # Search roster for invader in radius
                            for name, ship in self.world.roster.items():
                                if ship["team"] == cap["invader"]:
                                    dist = math.sqrt((ship["last_pos"][0]-cap["wx"])**2 + (ship["last_pos"][1]-cap["wz"])**2)
                                    if dist <= cap["radius"] * 1.5:
                                        cap["contests"].append({"t": clock, "wx": ship["last_pos"][0], "wz": ship["last_pos"][1], "team": ship["team"]})
                                        break
                    elif key == "invaderTeam":
                        cap["invader"] = val
