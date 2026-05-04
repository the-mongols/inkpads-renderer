import json

with open('arena_state.json') as f:
    d = json.load(f)

ps = d['payload']['OnArenaStateReceived']['player_states']
for p in ps:
    print(f"{p['username']}: {p['meta_ship_id']}")
