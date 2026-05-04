import json

def main():
    with open("arena_state.json", "r") as f:
        d = json.load(f)
    
    ps = d['payload']['OnArenaStateReceived']['player_states']
    mongols = [p for p in ps if p['username'] == 'The_Mongols'][0]
    my_team = mongols['team_id']
    my_id = mongols['entity_id']
    
    print(f"The_Mongols - Team: {my_team}, ID: {my_id}")
    
    teams = {0: [], 1: []}
    for p in ps:
        teams[p['team_id']].append(p['username'])
    
    print(f"Team 0: {len(teams[0])} players")
    print(f"Team 1: {len(teams[1])} players")
    
    # Check for capture points in the raw arena info if available
    # Sometimes it's in the first few packets but not in OnArenaStateReceived
    # Actually, we can get cap positions from the map asset later.

if __name__ == "__main__":
    main()
