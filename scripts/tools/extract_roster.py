import json
count = 0
try:
    with open('replayshark_dump.txt', encoding='utf-16') as f:
        for line in f:
            count += 1
            if count > 1000: break # Look further
            line = line.strip()
            if not line: continue
            try:
                data = json.loads(line)
                def hunt(obj):
                    if isinstance(obj, dict):
                        if "shipId" in obj and "name" in obj:
                            print(f"ROSTER: {obj['name']} -> shipId:{obj['shipId']} pid:{obj.get('shipParamsId', 0)}")
                        for v in obj.values(): hunt(v)
                    elif isinstance(obj, list):
                        for v in obj: hunt(v)
                hunt(data)
            except: pass
except Exception as e:
    print(f"File error: {e}")
