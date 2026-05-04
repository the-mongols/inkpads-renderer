import json
import subprocess
from pathlib import Path

# --- CONFIGURATION ---
REPLAY_PATH = r"C:\Users\arch\Downloads\20260416_214136_PRSC208-Tallin_41_Conquest.wowsreplay"
REPLAYSHARK_EXE = r"c:\Users\arch\Documents\weegeeDev\attempt2\target\release\replayshark.exe"
GAME_DIR = r"C:\Games\World_of_Warships"

# Forensic Constants for Trident (41_Conquest)
# space.settings bounds: -1165 to 1165 => Full width = 2330.0 units
SPACE_SIZE = 2330.0 

# Comprehensive Ship Mapping for Trident CB [KITE] vs [HHGA]
SHIP_DB = {
    4076778960: "Tallinn",
    4181669328: "Vladivostok",
    4181636528: "Cataluna",
    3762173936: "Kidd",
    4276008752: "Knesebeck",
    3667802064: "Cossack B",
    4181637104: "Bayard",
    3542037808: "Cherbourg",
    3531486928: "Shigure",
    3762206544: "Baltimore",
    4076779344: "Turgut Reis",
}

def resolve_ship_type(params_id, max_hp, name=""):
    if params_id in SHIP_DB: return SHIP_DB[params_id]
    if "Cherbourg" in name: return "Cherbourg"
    if "Tallinn" in name: return "Tallinn"
    if "Cataluna" in name: return "Cataluna"
    if "Kidd" in name: return "Kidd"
    if "Cossack" in name: return "Cossack B"
    
    if max_hp > 75000: return "Vladivostok"
    if 54000 < max_hp < 60000: return "Turgut Reis"
    if 60000 <= max_hp < 70000: return "Cherbourg"
    if 50000 <= max_hp < 53000: return "Knesebeck"
    if 48000 <= max_hp < 50000: return "Tallinn"
    if 41000 <= max_hp < 43000: return "Cataluna"
    if 20000 <= max_hp < 25000: return "Kidd"
    
    return "Unknown Ship"

def shred_replay(replay_path):
    print(f"--- Surgical Shred Engine V8: {Path(replay_path).name} ---")
    cmd = [REPLAYSHARK_EXE, "-g", GAME_DIR, "dump", replay_path]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)
    
    ships = {}
    sinking_events = []
    first_spotted = []
    smoke_trails = {} 
    pending_smokes = [] 
    spotted_ids = set()
    enemy_trails = {} 
    dead_ids = set()
    
    map_name = "Unknown"
    player_name = "Unknown"
    my_team = -1
    last_clock = 0
    
    for line in process.stdout:
        try:
            data = json.loads(line)
            if "mapName" in data:
                map_name = data.get("mapName", "Unknown")
                player_name = data.get("playerName", "Unknown")
                continue
            
            clock = data.get("clock", last_clock)
            last_clock = max(last_clock, clock)
            payload = data.get("payload", {})
            
            def hunt_roster(obj):
                nonlocal my_team
                if isinstance(obj, dict):
                    if "shipId" in obj and "name" in obj:
                        eid = obj["shipId"]; mhp = obj.get("maxHealth", 0); name = obj["name"]
                        team = obj.get("teamId", obj.get("relation", -1))
                        pid = obj.get("shipParamsId", 0)
                        if eid and name != "Unknown":
                            ships[eid] = {
                                "name": name, "params_id": pid,
                                "ship_type": resolve_ship_type(pid, mhp, name),
                                "team": team, "hp": mhp, "mhp": mhp,
                                "last_wx": 0.0, "last_wz": 0.0, "spotted": False,
                                "has_smoke": any(k in name or k in resolve_ship_type(pid, mhp, name) for k in ["Kidd", "Cossack", "Shigure"])
                            }
                            if name == player_name: my_team = team
                    for v in obj.values(): hunt_roster(v)
                elif isinstance(obj, list):
                    for v in obj: hunt_roster(v)

            hunt_roster(payload)

            if "EntityCreate" in payload:
                ec = payload["EntityCreate"]
                eid = ec["entity_id"]; etype = ec["entity_type"]
                props = ec.get("props", {})
                pos = ec.get("position", {"x": 0, "z": 0})
                
                if etype == "Vehicle" and eid not in ships:
                    mhp = props.get("maxHealth", 0); team = props.get("teamId", 0)
                    ships[eid] = {
                        "name": "Unknown", "params_id": 0,
                        "ship_type": resolve_ship_type(0, mhp),
                        "team": team, "hp": mhp, "mhp": mhp,
                        "last_wx": pos["x"], "last_wz": pos["z"], 
                        "spotted": False, "has_smoke": False
                    }
                elif etype == "SmokeScreen":
                    team = -1
                    for ps in reversed(pending_smokes):
                        if clock - ps["clock"] < 10.0:
                            team = ps["team"]; break
                    if team == -1:
                        ox, oz = pos["x"], pos["z"]
                        is_near_friendly = False
                        for sid, s in ships.items():
                            if s["team"] == my_team and s["has_smoke"]:
                                dx = s["last_wx"] - ox; dz = s["last_wz"] - oz
                                if (dx*dx + dz*dz) < 2000*2000:
                                    is_near_friendly = True; break
                        if not is_near_friendly: team = 1 - my_team
                    smoke_trails[eid] = {"points": [], "team": team}
                    for pt in props.get("points", []):
                        smoke_trails[eid]["points"].append((pt[0], pt[2]))

            if "Consumable" in payload:
                con = payload["Consumable"]
                eid = con.get("entity")
                ctype = con.get("consumable", {}).get("Known", "")
                if ctype == "Smoke" and eid in ships:
                    pending_smokes.append({"clock": clock, "team": ships[eid]["team"]})

            if "PropertyUpdate" in payload:
                pu = payload["PropertyUpdate"]
                eid = pu["entity_id"]
                if eid in smoke_trails and pu["property"] == "points":
                    cmd = pu.get("update_cmd", {}); action = cmd.get("action", {})
                    if "SetRange" in action:
                        for pt in action["SetRange"].get("values", []):
                            pt_w = (pt[0], pt[2])
                            if pt_w not in smoke_trails[eid]["points"]:
                                smoke_trails[eid]["points"].append(pt_w)

            if "MinimapUpdate" in payload:
                for up in payload["MinimapUpdate"].get("updates", []):
                    sid = up["entity_id"]
                    if sid not in ships: continue
                    nx, ny = up["position"]["x"], up["position"]["y"]
                    # Use Clinical SPACE_SIZE
                    wx = (nx - 0.5) * SPACE_SIZE
                    wz = (ny - 0.5) * SPACE_SIZE
                    s = ships[sid]
                    if sid not in spotted_ids and s["team"] != my_team:
                        spotted_ids.add(sid)
                        first_spotted.append({"ship": s["ship_type"], "wx": wx, "wz": wz})
                    
                    if s["team"] != my_team:
                        if sid not in enemy_trails: enemy_trails[sid] = {"path": []}
                        enemy_trails[sid]["path"].append((wx, wz))
                    s["last_wx"], s["last_wz"] = wx, wz

            if "EntityProperty" in payload:
                ep = payload["EntityProperty"]
                eid = ep["entity_id"]; prop = ep["property"]; val = ep["value"]
                if eid in ships and prop == "health":
                    s = ships[eid]
                    if val <= 0 and s["hp"] > 0 and eid not in dead_ids:
                        if s["team"] == my_team:
                             print(f"DEATH (HP): {s['ship_type']} at {s['last_wx']}, {s['last_wz']}")
                             sinking_events.append({"wx": s["last_wx"], "wz": s["last_wz"], "ship": s["ship_type"]})
                             dead_ids.add(eid)
                    s["hp"] = val

            if "ShotKills" in payload:
                sk = payload["ShotKills"]
                for hit in sk.get("hits", []):
                    vid = hit.get("owner_id")
                    if vid in ships and vid not in dead_ids:
                        s = ships[vid]
                        if s["team"] == my_team:
                            print(f"DEATH (KILL): {s['ship_type']} at {s['last_wx']}, {s['last_wz']}")
                            sinking_events.append({"wx": s["last_wx"], "wz": s["last_wz"], "ship": s["ship_type"]})
                            dead_ids.add(vid)

        except Exception as e: continue
    process.wait()
    
    enemy_smoke_export = []
    for eid, t in smoke_trails.items():
        if t["team"] != my_team and t["team"] != -1:
            for pt in t["points"]:
                enemy_smoke_export.append({"ship": f"Smoke_{eid}", "wx": pt[0], "wz": pt[1]})

    return {
        "enemy_smoke_events": enemy_smoke_export,
        "first_spot_events": first_spotted,
        "sinking_events": sinking_events,
        "enemy_trails": list(enemy_trails.values())
    }

if __name__ == "__main__":
    import sys
    replay = sys.argv[1] if len(sys.argv) > 1 else REPLAY_PATH
    result = shred_replay(replay)
    with open("salem_shredded_data.json", "w") as f:
        json.dump(result, f, indent=4)
    print("Surgical Shred V8 complete.")
