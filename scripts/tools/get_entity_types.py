import json
import sys

def main():
    types = set()
    with open("replayshark_dump.txt", "r", encoding="utf-8") as f:
        for line in f:
            try:
                data = json.loads(line)
                payload = data.get("payload", {})
                if "EntityCreate" in payload:
                    types.add(payload["EntityCreate"].get("entity_type"))
            except:
                continue
    print("Unique Entity Types:")
    for t in sorted(list(types)):
        print(f" - {t}")

if __name__ == "__main__":
    main()
