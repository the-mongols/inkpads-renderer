import json
from pathlib import Path
from .world import WorldState
from .parser import ReplayParser
from .extractors import RosterExtractor, MovementExtractor, CombatExtractor, ObjectiveExtractor
from map_resolver import MapResolver

class ForensicEngine:
    """
    The main coordinator for the Shredder Engine 2.0.
    """
    def __init__(self, replayshark_exe, game_dir):
        self.world = WorldState()
        self.parser = ReplayParser(replayshark_exe, game_dir)
        self.resolver = MapResolver(game_dir=game_dir, unpacker_exe=str(Path(replayshark_exe).parent / "wowsunpack.exe"))
        
        # Load Ship Mapping
        if Path("ship_mapping.json").exists():
            with open("ship_mapping.json") as f:
                self.world.ship_mapping = json.load(f)

        # Register Extractors
        self.extractors = [
            RosterExtractor(self.world),
            MovementExtractor(self.world),
            CombatExtractor(self.world),
            ObjectiveExtractor(self.world)
        ]
        
        for ext in self.extractors:
            self.parser.register_handler(ext.handle)
            
        self.parser.register_handler(self._internal_handler)

    def _internal_handler(self, packet_type, data, clock):
        """
        Handles engine-level logic like map resolution and calibration.
        """
        if packet_type == "header":
            map_name = data.get("mapName")
            self.world.map_name = map_name
            # Resolve map assets/bounds
            map_meta = self.resolver.resolve(map_name)
            self.world.space_size = map_meta.get("space_size", 0)
            if self.world.space_size > 0:
                self.world.is_calibrated = True

        elif packet_type == "CellPlayerCreate":
            # Used for auto-calibration if space_size is still 0
            pos = data.get("position", {})
            props = data.get("props", {})
            own_sid = props.get("ownShipId")
            if own_sid:
                self.world.calibration_points.append({
                    "sid": own_sid, "wx": pos.get("x"), "wz": pos.get("z")
                })

        elif packet_type == "MinimapUpdate" and not self.world.is_calibrated:
            for up in data.get("updates", []):
                sid = up["entity_id"]
                for cp in self.world.calibration_points:
                    if cp["sid"] == sid:
                        self.world.calibrate(sid, cp["wx"], cp["wz"], up["position"]["x"], up["position"]["y"])
                        break

    def run(self, replay_path):
        self.parser.run(replay_path)
        return self.finalize()

    def finalize(self):
        report = {
            "metadata": {
                "player": self.world.player_name,
                "team": self.world.my_team,
                "map": self.world.map_name,
                "space_size": self.world.space_size,
                "roster": self.world.roster
            },
            "telemetry": {}
        }
        
        for ext in self.extractors:
            report["telemetry"].update(ext.finalize())
            
        return report

if __name__ == "__main__":
    # Test stub
    import sys
    REPLAY = r"C:\Users\arch\Downloads\20260416_214136_PRSC208-Tallin_41_Conquest.wowsreplay"
    EXE = r"c:\Users\arch\Documents\weegeeDev\attempt2\target\release\replayshark.exe"
    GAME = r"C:\Games\World_of_Warships"
    
    engine = ForensicEngine(EXE, GAME)
    report = engine.run(REPLAY)
    
    with open("forensic_report_v2.json", "w") as f:
        json.dump(report, f, indent=4)
    print("Forensic Engine 2.0: Report generated -> forensic_report_v2.json")
