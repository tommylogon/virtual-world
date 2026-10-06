import json
from virtual_world_engine import VirtualWorld
import os

world = VirtualWorld()
template_path = 'world_template.json'
if os.path.exists(template_path):
    with open(template_path, 'r', encoding='utf-8-sig') as f:
        template_data = json.load(f)
    world.load_from_dict(template_data)

state = world.to_dict()
full = json.dumps(state)
print(f'Full payload: {len(full) / 1024 / 1024:.2f} MB')

graph_only = json.dumps(state.get('graph', {}))
print(f'Graph only: {len(graph_only) / 1024 / 1024:.2f} MB')

areas = state.get('areas', {})
print(f'Areas projection: {len(json.dumps(areas)) / 1024 / 1024:.2f} MB')

players = state.get('players', {})
print(f'Players: {len(json.dumps(players)) / 1024 / 1024:.2f} MB')

ways = state.get('ways', {})
print(f'Ways: {len(json.dumps(ways)) / 1024 / 1024:.2f} MB')

item_reg = state.get('item_registry', {})
print(f'Item registry: {len(json.dumps(item_reg)) / 1024 / 1024:.2f} MB')

world_scopes = state.get('world_scopes', {})
print(f'World scopes: {len(json.dumps(world_scopes)) / 1024 / 1024:.2f} MB')

world_index = state.get('world_index', {})
print(f'World index: {len(json.dumps(world_index)) / 1024 / 1024:.2f} MB')

game_log = state.get('game_log', [])
print(f'Game log: {len(json.dumps(game_log)) / 1024 / 1024:.2f} MB')

turn_events = state.get('turn_events', [])
print(f'Turn events: {len(json.dumps(turn_events)) / 1024 / 1024:.2f} MB')

print(f'Nodes: {len(state["graph"]["nodes"])}')
print(f'Edges: {len(state["graph"]["edges"])}')
