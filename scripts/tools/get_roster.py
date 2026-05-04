import json
import subprocess

def get_roster(target_file):
    # ReplayShark dump starts with a JSON blob containing the roster
    cmd = [r"target\release\replayshark.exe", "-g", r"C:\Games\World_of_Warships", "dump", target_file]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)
    
    first_packet = ""
    for line in process.stdout:
        if line.strip().startswith("{"):
            first_packet = line.strip()
            break
    process.terminate()
    
    if first_packet:
        data = json.loads(first_packet)
        vehicles = data.get("vehicles", [])
        # Also check playerVehicle for the recorder
        recorder_name = data.get("playerName")
        recorder_ship = data.get("playerVehicle")
        
        print(f"Recorder: {recorder_name} -> {recorder_ship}")
        for v in vehicles:
            print(f"Player: {v.get('name')}, ShipID: {v.get('shipId')}, ID: {v.get('id')}")

get_roster(r"C:\Users\arch\Downloads\20260416_212807_PRSC208-Tallin_15_NE_north.wowsreplay")
