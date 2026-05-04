import json
import subprocess
import math
import re
from pathlib import Path
from map_resolver import MapResolver

class ReplayShredder:
    def __init__(self, replay_path, replayshark_exe, game_dir):
        self.replay_path = Path(replay_path)
        self.replayshark_exe = replayshark_exe
        self.game_dir = game_dir
        self.resolver = MapResolver(game_dir=game_dir, unpacker_exe=str(Path(replayshark_exe).parent / "wowsunpack.exe"))
        
        self.map_meta = None
        self.roster = {}
        self.player_name = None
        self.my_team = -1
        
        self.ship_mapping = {}
        self.load_ship_mapping()
        
        self.events = {
            "movements": {},   
            "spots": [],       
            "deaths": [],      
            "caps": {},        
            "damage": [],      
            "shots": [],       
            "consumables": []
        }
        
        self.spotted_sids = set()
        self.dead_sids = set()
        self.sid_to_name = {} 
        self.cap_sids = set()
        
        self.dwell_matrices = {
            0: [[0 for _ in range(100)] for _ in range(100)],
            1: [[0 for _ in range(100)] for _ in range(100)],
            2: [[0 for _ in range(100)] for _ in range(100)]
        }
        
        self.last_hp = {} 
        self.calibration_points = []
        self.calibrated_size = None

    def load_ship_mapping(self):
        try:
            with open("ship_mapping.json", "r", encoding="utf-8") as f:
                self.ship_mapping = json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load ship_mapping.json: {e}")

    def resolve_ship(self, params_id, raw_name="Unknown"):
        if str(params_id) in self.ship_mapping:
            info = self.ship_mapping[str(params_id)]
            return info["name"], info["species"]
        
        clean = raw_name
        if "-" in raw_name:
            clean = raw_name.split("-")[-1]
        
        species = "Unknown"
        if "PRSC" in raw_name or "PASC" in raw_name: species = "Cruiser"
        elif "PRSB" in raw_name or "PASB" in raw_name: species = "Battleship"
        elif "PRSD" in raw_name or "PASD" in raw_name: species = "Destroyer"
        
        return clean, species

    def run(self):
        print(f"--- Forensic Shredder V9.2: {self.replay_path.name} ---")
        if not self.ship_mapping:
            print("Ship mapping missing. Generating...")
            subprocess.run(["python", "extract_ship_names.py"], check=False)
            self.load_ship_mapping()

        cmd = [self.replayshark_exe, "-g", self.game_dir, "dump", str(self.replay_path)]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True, encoding='utf-8')
        
        for line in process.stdout:
            try:
                data = json.loads(line)
                if "mapName" in data:
                    self.process_header(data)
                    continue
                
                clock = data.get("clock", 0)
                payload = data.get("payload", {})
                
                self.hunt_entity_links(payload)

                if "EntityCreate" in payload:
                    self.process_entity_create(payload["EntityCreate"], clock)
                
                if "CellPlayerCreate" in payload:
                    self.process_cell_player_create(payload["CellPlayerCreate"], clock)
                
                if "MinimapUpdate" in payload:
                    self.process_minimap_update(payload["MinimapUpdate"], clock)
                    
                if "EntityProperty" in payload:
                    self.process_entity_property(payload["EntityProperty"], clock)
                
                if "PropertyUpdate" in payload:
                    self.process_property_update(payload["PropertyUpdate"], clock)

                if "ArtilleryShots" in payload:
                    self.process_artillery_shots(payload["ArtilleryShots"], clock)

                if "ShotKills" in payload:
                    self.process_shot_kills(payload["ShotKills"], clock)

            except Exception:
                continue
        
        process.wait()
        return self.finalize()

    def process_header(self, data):
        self.player_name = data.get("playerName")
        map_name = data.get("mapName")
        self.map_meta = self.resolver.resolve(map_name)
        
        for v in data.get("vehicles", []):
            pname = v.get("name")
            raw_ship = v.get("playerVehicle", "Unknown")
            params_id = v.get("shipParamsId", 0)
            ship_name, species = self.resolve_ship(params_id, raw_ship)
            
            self.roster[pname] = {
                "name": pname,
                "ship_type": ship_name,
                "species": species,
                "team": v.get("relation"),
                "sid": None,
                "last_pos": (0, 0)
            }
            if pname == self.player_name:
                self.my_team = v.get("relation")

    def hunt_entity_links(self, obj):
        if isinstance(obj, dict):
            if "name" in obj and "shipId" in obj:
                pname = obj["name"]
                if pname in self.roster:
                    sid = obj["shipId"]
                    self.roster[pname]["sid"] = sid
                    self.sid_to_name[sid] = pname
                    if "shipParamsId" in obj:
                        ship_name, species = self.resolve_ship(obj["shipParamsId"])
                        self.roster[pname]["ship_type"] = ship_name
                        self.roster[pname]["species"] = species
            
            for v in obj.values(): self.hunt_entity_links(v)
        elif isinstance(obj, list):
            for v in obj: self.hunt_entity_links(v)

    def process_cell_player_create(self, cpc, clock):
        props = cpc.get("props", {})
        pos = cpc.get("position", {})
        own_ship_id = props.get("ownShipId")
        
        if self.player_name in self.roster:
            self.roster[self.player_name]["sid"] = own_ship_id
            self.sid_to_name[own_ship_id] = self.player_name
            self.calibration_points.append({"wx": pos["x"], "wz": pos["z"], "nx": None, "ny": None})

    def process_entity_create(self, ec, clock):
        etype = ec.get("entity_type")
        props = ec.get("props", {})
        pos = ec.get("position", {})
        eid = ec.get("entity_id")
        
        if etype == "InteractiveZone":
            comp = props.get("componentsState", {})
            cp = comp.get("controlPoint")
            if cp:
                self.cap_sids.add(eid)
                self.events["caps"][eid] = {
                    "index": cp.get("index"),
                    "wx": pos.get("x"),
                    "wz": pos.get("z"),
                    "radius": props.get("radius"),
                    "owner": props.get("teamId", -1),
                    "ownership_duration": {0: 0, 1: 0, 2: 0},
                    "last_owner_change": clock,
                    "progress": 0.0,
                    "invader": -1,
                    "contests": [] # list of (clock, wx, wz, team)
                }
        
        if etype == "Vehicle":
            self.last_hp[eid] = props.get("maxHealth", 0)
            pname = props.get("name")
            if pname and pname in self.roster:
                self.roster[pname]["sid"] = eid
                self.sid_to_name[eid] = pname
            
            if eid == self.roster.get(self.player_name, {}).get("sid"):
                self.calibration_points.append({"wx": pos["x"], "wz": pos["z"], "nx": None, "ny": None})

    def process_minimap_update(self, mu, clock):
        for up in mu.get("updates", []):
            sid = up["entity_id"]
            if sid not in self.sid_to_name: continue
            
            pname = self.sid_to_name[sid]
            ship = self.roster[pname]
            nx, ny = up["position"]["x"], up["position"]["y"]
            
            if sid == ship.get("sid") and self.calibrated_size is None:
                for cp in self.calibration_points:
                    if cp["nx"] is None:
                        cp["nx"], cp["ny"] = nx, ny
                        dx = nx - 0.5
                        if abs(dx) > 0.01:
                            self.calibrated_size = abs(cp["wx"] / dx)
                            self.map_meta["space_size"] = self.calibrated_size
                            break

            size = self.calibrated_size or self.map_meta["space_size"]
            wx = (nx - 0.5) * size
            wz = (ny - 0.5) * size
            ship["last_pos"] = (wx, wz)
            
            gx, gy = int(nx * 100), int(ny * 100)
            if 0 <= gx < 100 and 0 <= gy < 100:
                self.dwell_matrices[ship["team"]][gy][gx] += 1
            
            if ship["team"] != self.my_team:
                if sid not in self.events["movements"]: self.events["movements"][sid] = []
                self.events["movements"][sid].append({"clock": clock, "wx": wx, "wz": wz})
                
                if sid not in self.spotted_sids:
                    self.spotted_sids.add(sid)
                    self.events["spots"].append({
                        "clock": clock, "sid": sid, "wx": wx, "wz": wz,
                        "ship": ship["ship_type"], "species": ship["species"], "player": pname
                    })

    def process_entity_property(self, ep, clock):
        sid = ep.get("entity_id")
        prop = ep.get("property")
        val = ep.get("value")
        
        if sid in self.sid_to_name and prop == "health":
            ship = self.roster[self.sid_to_name[sid]]
            if ship["team"] == self.my_team:
                last = self.last_hp.get(sid)
                if last is not None and val < last:
                    wx, wz = ship["last_pos"]
                    self.events["damage"].append({
                        "clock": clock, "wx": wx, "wz": wz, "dmg": last - val,
                        "ship": ship["ship_type"]
                    })
                self.last_hp[sid] = val
            if val <= 0:
                self.record_death(sid, clock)
        
        if sid in self.cap_sids and prop == "teamId":
            cap = self.events["caps"][sid]
            # Record ownership duration for previous owner
            if cap["owner"] != -1:
                cap["ownership_duration"][cap["owner"]] += (clock - cap["last_owner_change"])
            cap["owner"] = val
            cap["last_owner_change"] = clock

    def process_property_update(self, pu, clock):
        sid = pu.get("entity_id")
        prop = pu.get("property")
        if sid in self.cap_sids and prop == "componentsState":
            cmd = pu.get("update_cmd", {})
            levels = cmd.get("levels", [])
            action = cmd.get("action", {})
            
            if levels and levels[0].get("DictKey") == "captureLogic":
                cap = self.events["caps"][sid]
                if "SetKey" in action:
                    key = action["SetKey"].get("key")
                    val = action["SetKey"].get("value")
                    if key == "progress": 
                        cap["progress"] = val
                        # Record contest location if progress changed by an invader
                        if cap["invader"] != -1 and val > 0:
                            # Try to find an invader from the invaderTeam within radius
                            for pname, ship in self.roster.items():
                                if ship["team"] == cap["invader"]:
                                    wx, wz = ship["last_pos"]
                                    dist = math.sqrt((wx - cap["wx"])**2 + (wz - cap["wz"])**2)
                                    if dist <= cap["radius"] * 1.5: # Allow some buffer
                                        cap["contests"].append({"clock": clock, "wx": wx, "wz": wz, "team": cap["invader"]})
                                        break
                    if key == "invaderTeam": cap["invader"] = val

    def process_artillery_shots(self, ashots, clock):
        salvos = ashots.get("salvos", [])
        for salvo in salvos:
            sid = salvo.get("owner_id")
            for s in salvo.get("shots", []):
                origin = s.get("origin", {})
                target = s.get("target", {})
                self.events["shots"].append({
                    "clock": clock, "sid": sid,
                    "ox": origin.get("x"), "oz": origin.get("z"),
                    "tx": target.get("x"), "tz": target.get("z")
                })

    def process_shot_kills(self, sk, clock):
        for hit in sk.get("hits", []):
            sid = hit.get("owner_id")
            if sid in self.sid_to_name: self.record_death(sid, clock)

    def record_death(self, sid, clock):
        if sid not in self.dead_sids:
            self.dead_sids.add(sid)
            pname = self.sid_to_name.get(sid)
            if not pname: return
            ship = self.roster[pname]
            wx, wz = ship["last_pos"]
            
            if ship["species"] == "Battleship":
                self.events["deaths"].append({
                    "clock": clock, "sid": sid, "wx": wx, "wz": wz,
                    "ship": ship["ship_type"], "team": ship["team"],
                    "player": ship["name"], "is_bb": True
                })

    def finalize(self):
        # Final clock to calculate duration
        final_clock = 0
        for m in self.events["movements"].values():
            if m: final_clock = max(final_clock, m[-1]["clock"])

        # Link shots to player names if possible
        for s in self.events["shots"]:
            sid = s["sid"]
            if sid in self.sid_to_name:
                pname = self.sid_to_name[sid]
                s["player"] = pname
                s["team"] = self.roster[pname]["team"]
                s["ship"] = self.roster[pname]["ship_type"]
            else:
                s["player"] = "Unknown"
                s["team"] = -1
                s["ship"] = "Unknown"
        
        # Finalize cap ownership duration
        for cap in self.events["caps"].values():
            if cap["owner"] != -1:
                cap["ownership_duration"][int(cap["owner"])] += (final_clock - cap["last_owner_change"])

        return {
            "metadata": {
                "player": self.player_name,
                "my_team": self.my_team,
                "map": self.map_meta,
                "roster": self.roster,
                "dwell_matrices": self.dwell_matrices
            },
            "events": self.events
        }

if __name__ == "__main__":
    REPLAY = r"C:\Users\arch\Downloads\20260416_214136_PRSC208-Tallin_41_Conquest.wowsreplay"
    EXE = r"c:\Users\arch\Documents\weegeeDev\attempt2\target\release\replayshark.exe"
    GAME = r"C:\Games\World_of_Warships"
    
    shredder = ReplayShredder(REPLAY, EXE, GAME)
    report = shredder.run()
    
    with open("match_report.json", "w") as f:
        json.dump(report, f, indent=4)
    print("Forensic Match Report generated: match_report.json")
