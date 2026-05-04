import json
import sys

def main():
    print("Loading specs.json...")
    with open("specs.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    mapping = {}
    print("Scanning for ships...")
    for key, value in data.items():
        if not isinstance(value, dict):
            continue
        
        # Check if it's a ship
        if value.get("typeinfo", {}).get("type") == "Ship":
            ship_id = value.get("id")
            typeinfo = value.get("typeinfo", {})
            species = typeinfo.get("species")
            tier = typeinfo.get("tier")
            nation = typeinfo.get("nation")
            
            human_name = key
            if "-" in key:
                human_name = key.split("-")[-1]
            
            if "name" in value:
                human_name = value["name"]
                
            if ship_id is not None:
                mapping[ship_id] = {
                    "name": human_name,
                    "species": species,
                    "tier": tier,
                    "nation": nation
                }
    
    print(f"Found {len(mapping)} ships.")
    with open("ship_mapping.json", "w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=4)
    print("Saved to ship_mapping.json")

if __name__ == "__main__":
    main()
