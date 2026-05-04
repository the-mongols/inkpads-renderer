import json
try:
    with open('replayshark_dump.txt', encoding='utf-16') as f:
        for line in f:
            if '"SmokeScreen"' in line or '"points"' in line:
                if 'entity_id' in line:
                    print(line.strip())
except Exception as e:
    print(e)
