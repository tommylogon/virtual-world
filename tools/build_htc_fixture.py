import json
import os
import copy

with open('tools/miki_template.json', 'r', encoding='utf-8') as f:
    template = json.load(f)

def make_player_dict(name, pid, is_simple=False, behaviors=None, known=None, preconceived=None):
    p = copy.deepcopy(template)
    p['name'] = name
    p['id'] = pid
    p['simple_npc'] = is_simple
    p['autonomy'] = not is_simple
    p['behaviors'] = behaviors or []
    p['known'] = known or []
    if preconceived:
        p['preconceived_knowledge'] = preconceived
    p['discovered_exits'] = []
    p['memories'] = []
    p['relationships'] = {}
    p['current_area'] = None
    p['grappled_by'] = None
    p['at_way_id'] = None
    p['facing'] = None
    p['entered_from_way'] = None
    p['spatial_position'] = None
    if is_simple:
        p['npc_behavior'] = 'wander'
        p['npc_action_interval'] = 1
        p['npc_state'] = 'idle'
        p['state_enter_tick'] = 0
    return p

areas_def = [
    ('area_courtyard', 'Courtyard', 0, 0, 'an open cobbled courtyard surrounded by ancient stone walls.'),
    ('area_hall', 'Great Hall', 1, 0, 'a grand hall with high ceilings and banners hanging from the walls.'),
    ('area_armory', 'Armory', 2, 0, 'a secured chamber stocked with weapons and sturdy racks.'),
    ('area_parapet', 'Parapet', 3, 0, 'an elevated walkway overlooking the perimeter.'),
    ('area_kitchen', 'Kitchen', 0, 1, 'a warm kitchen with a large hearth and prep tables.'),
    ('area_pantry', 'Pantry', 1, 1, 'a cool pantry lined with shelves and provisions.'),
    ('area_guard_room', 'Guard Room', 2, 1, 'a fortified station where the keep guards keep watch.'),
    ('area_tower_base', 'Tower Base', 3, 1, 'the circular base of the watchtower with winding stairs.'),
    ('area_garden', 'Garden', 0, 2, 'a secluded overgrown garden filled with wild herbs.'),
    ('area_library', 'Library', 1, 2, 'a quiet sanctuary lined with towering bookshelves.'),
    ('area_secret_vault', 'Secret Vault', 2, 2, 'a hidden stone vault concealed behind the bookshelves.'),
    ('area_dungeon', 'Dungeon Cell', 3, 2, 'a dark cell with heavy damp walls and iron shackles.'),
]

nodes = {}
edges = []
area_placements = {}

for aid, aname, cx, cy, desc in areas_def:
    nodes[aid] = {
        'id': aid,
        'type': 'area',
        'name': aname,
        'properties': {
            'cell': {'x': cx, 'y': cy},
            'world_scope_id': 'htc_scope',
            'description': desc,
            'environment': {
                'air': 'fresh',
                'light': 80,
                'noise': 'quiet',
                'smell': 'stone and wood',
                'temperature': 20
            },
            'x': cx * 100,
            'y': cy * 100
        }
    }
    area_placements[aid] = {'x': cx, 'y': cy}

def connect_areas(way_id, way_name, from_id, to_id, from_dir, to_dir, pass_msg, state='open', desc='a standard doorway'):
    nodes[way_id] = {
        'id': way_id,
        'type': 'way',
        'name': way_name,
        'properties': {
            'area_from': from_id,
            'area_to': to_id,
            'direction': from_dir,
            'return_direction': to_dir,
            'current_state': state,
            'pass_message': pass_msg,
            'description': desc,
            'world_scope_id': 'htc_scope',
            'cost': {'time': 1}
        }
    }
    edges.append({'source': from_id, 'target': way_id, 'type': 'connection', 'properties': {'direction': from_dir}})
    edges.append({'source': way_id, 'target': to_id, 'type': 'connection', 'properties': {'direction': to_dir}})

# Grid connections
connect_areas('way_courtyard_hall', 'courtyard-hall archway', 'area_courtyard', 'area_hall', 'east', 'west', 'You pass under the stone archway into the Great Hall.')
connect_areas('way_hall_armory', 'heavy oak door', 'area_hall', 'area_armory', 'east', 'west', 'You unlock and push through the heavy oak door into the Armory.', state='locked', desc='a reinforced door bound in iron, firmly locked.')
connect_areas('way_armory_parapet', 'parapet door', 'area_armory', 'area_parapet', 'east', 'west', 'You step out onto the windy parapet walkway.')
connect_areas('way_courtyard_kitchen', 'kitchen doorway', 'area_courtyard', 'area_kitchen', 'south', 'north', 'You walk down the stone steps into the warm kitchen.')
connect_areas('way_hall_pantry', 'pantry doorway', 'area_hall', 'area_pantry', 'south', 'north', 'You step through the archway into the cool pantry.')
connect_areas('way_armory_guard_room', 'guard room door', 'area_armory', 'area_guard_room', 'south', 'north', 'You pass into the busy guard station.')
connect_areas('way_parapet_tower_base', 'tower stairs', 'area_parapet', 'area_tower_base', 'south', 'north', 'You descend the stairs into the tower base.')
connect_areas('way_kitchen_pantry', 'kitchen pantry arch', 'area_kitchen', 'area_pantry', 'east', 'west', 'You move between the kitchen and pantry.')
connect_areas('way_pantry_guard_room', 'pantry guard hall', 'area_pantry', 'area_guard_room', 'east', 'west', 'You walk down the corridor to the guard room.')
connect_areas('way_guard_room_tower_base', 'guard tower passage', 'area_guard_room', 'area_tower_base', 'east', 'west', 'You proceed through the fortified corridor to the tower base.')
connect_areas('way_kitchen_garden', 'garden gate', 'area_kitchen', 'area_garden', 'south', 'north', 'You step out through the wooden gate into the garden.')
connect_areas('way_pantry_library', 'library door', 'area_pantry', 'area_library', 'south', 'north', 'You push open the quiet door into the library.')
connect_areas('way_library_vault', 'false bookcase wall', 'area_library', 'area_secret_vault', 'east', 'west', 'You slide the false bookcase aside and slip into the vault.', state='hidden', desc='a false wall panel concealed perfectly behind towering oak shelves.')
connect_areas('way_vault_dungeon', 'collapsed passage', 'area_secret_vault', 'area_dungeon', 'east', 'west', 'You squeeze through the rubble into the dungeon cell.', state='blocked', desc='a collapsed stone tunnel choked with fallen granite blocks.')
connect_areas('way_garden_library', 'terrace doors', 'area_garden', 'area_library', 'east', 'west', 'You walk from the garden terrace into the library.')
connect_areas('way_tower_base_dungeon', 'dungeon stairs', 'area_tower_base', 'area_dungeon', 'south', 'north', 'You descend the cold winding stone stairs into the dungeon.')

# Characters
# 1. Human player
nodes['player_explorer'] = {
    'id': 'player_explorer',
    'type': 'character',
    'name': 'Explorer',
    'properties': {
        'description': 'a seasoned explorer with keen eyes and rugged travel gear.',
        'personality': 'You are the intrepid Explorer examining the forgotten keep.',
        'tags': ['human', 'player'],
        'world_scope_id': 'htc_scope',
        'x': 50,
        'y': 50
    }
}
edges.append({'source': 'player_explorer', 'target': 'area_courtyard', 'type': 'in', 'properties': {}})

# 2. Guard 1 in Guard Room
nodes['player_guard'] = {
    'id': 'player_guard',
    'type': 'character',
    'name': 'Guard',
    'properties': {
        'description': 'a tall sentry standing watch in polished steel armor.',
        'personality': 'A stern keep guard on duty.',
        'tags': ['guard', 'sentry'],
        'world_scope_id': 'htc_scope',
        'x': 250,
        'y': 150
    }
}
edges.append({'source': 'player_guard', 'target': 'area_guard_room', 'type': 'in', 'properties': {}})

# 3. Guard 2 in Guard Room (Same display name, same area, registry key Guard__b2b2b2)
nodes['player_guard__b2b2b2'] = {
    'id': 'player_guard__b2b2b2',
    'type': 'character',
    'name': 'Guard',
    'properties': {
        'description': 'a scarred veteran guard polishing a heavy crossbow.',
        'personality': 'An experienced veteran guard keeping an eye on the perimeter.',
        'tags': ['guard', 'veteran'],
        'world_scope_id': 'htc_scope',
        'x': 270,
        'y': 150
    }
}
edges.append({'source': 'player_guard__b2b2b2', 'target': 'area_guard_room', 'type': 'in', 'properties': {}})

# 4. Doctor Brown in Library with nickname "Doc"
nodes['player_doctor_brown'] = {
    'id': 'player_doctor_brown',
    'type': 'character',
    'name': 'Doctor Brown',
    'properties': {
        'description': 'an eccentric scholar with spectacles and wild white hair.',
        'personality': 'An academic historian researching ancient manuscripts.',
        'aliases': ['Doc'],
        'tags': ['scholar', 'doctor'],
        'world_scope_id': 'htc_scope',
        'x': 150,
        'y': 250
    }
}
edges.append({'source': 'player_doctor_brown', 'target': 'area_library', 'type': 'in', 'properties': {}})

# 5. Doc Holliday in Courtyard with nickname "Doc"
nodes['player_doc_holliday'] = {
    'id': 'player_doc_holliday',
    'type': 'character',
    'name': 'Doc Holliday',
    'properties': {
        'description': 'a sharp-dressed gambler with a pale face and cold eyes.',
        'personality': 'A notorious gunslinger taking in the evening air.',
        'aliases': ['Doc'],
        'tags': ['gambler'],
        'world_scope_id': 'htc_scope',
        'x': 70,
        'y': 50
    }
}
edges.append({'source': 'player_doc_holliday', 'target': 'area_courtyard', 'type': 'in', 'properties': {}})

# 6. Crypt Ghoul (simple_npc with zombie behaviors) in Dungeon Cell
zombie_behaviors = [
    {
        'trigger': 'on_player_enter_room',
        'interval': 1,
        'priority': 0,
        'conditions': {'type': 'eq', 'target': 'npc_state', 'value': 'idle'},
        'actions': [
            {'type': 'message', 'text': 'A hollow rasp echoes from the shadows as the crypt ghoul turns toward you.'},
            {'type': 'set_npc_state', 'state': 'angry'}
        ]
    },
    {
        'trigger': 'on_player_enter_area',
        'interval': 1,
        'priority': 0,
        'conditions': {'type': 'eq', 'target': 'npc_state', 'value': 'angry'},
        'actions': [
            {'type': 'speak', 'text': 'The ghoul lunges with blackened claws, swiping at your throat!'},
            {'type': 'damage', 'target': 'player', 'amount': 6}
        ]
    },
    {
        'trigger': 'on_tick',
        'interval': 1,
        'priority': 0,
        'conditions': {},
        'actions': [
            {'type': 'speak', 'text': 'Hhhhh... flesh...'}
        ]
    },
    {
        'trigger': 'on_speech_heard',
        'interval': 1,
        'priority': 0,
        'conditions': {},
        'actions': [
            {'type': 'go', 'mode': 'random'}
        ]
    },
    {
        'trigger': 'on_player_leave_area',
        'interval': 1,
        'priority': 0,
        'conditions': {},
        'actions': [
            {'type': 'set_npc_state', 'state': 'idle'}
        ]
    }
]

nodes['player_crypt_ghoul'] = {
    'id': 'player_crypt_ghoul',
    'type': 'character',
    'name': 'Crypt Ghoul',
    'properties': {
        'description': 'a gaunt withered creature with glowing pale eyes and jagged claws.',
        'personality': 'A ravenous undead ghoul dwelling in the dark.',
        'tags': ['undead', 'monster', 'ghoul'],
        'world_scope_id': 'htc_scope',
        'x': 350,
        'y': 250
    }
}
edges.append({'source': 'player_crypt_ghoul', 'target': 'area_dungeon', 'type': 'in', 'properties': {}})

# Items
# 1. Ancient Relic with on_examine flavor trigger
nodes['item_ancient_relic'] = {
    'id': 'item_ancient_relic',
    'type': 'item',
    'name': 'ancient_relic',
    'properties': {
        'name': 'ancient_relic',
        'description': 'a weathered stone artifact carved with glowing celestial runes.',
        'weight': 1.0,
        'uses': -1,
        'actions': ['examine', 'take', 'drop'],
        'action_costs': {'examine': {'time': 1}},
        'tags': ['artifact', 'magic', 'relic'],
        'triggers': [
            {
                'id': 'trigger_item_ancient_relic_on_examine',
                'trigger_type': 'on_examine',
                'target_name': '',
                'conditions': [],
                'conditions_logic': 'and',
                'effects': [
                    {
                        'type': 'message',
                        'params': {
                            'message': '',
                            'success_message': 'The runes flare with azure light as faint whispers fill your mind.'
                        }
                    }
                ]
            }
        ],
        'world_scope_id': 'htc_scope',
        'x': 120,
        'y': 70
    }
}
edges.append({'source': 'item_ancient_relic', 'target': 'area_courtyard', 'type': 'in', 'properties': {}})

# 2. Sparring Dummy (grapple target prop)
nodes['item_sparring_dummy'] = {
    'id': 'item_sparring_dummy',
    'type': 'item',
    'name': 'sparring_dummy',
    'properties': {
        'name': 'sparring_dummy',
        'description': 'a heavy canvas and straw combat dummy mounted on an iron swivel base.',
        'weight': 25.0,
        'uses': -1,
        'actions': ['examine', 'take'],
        'tags': ['training', 'prop'],
        'world_scope_id': 'htc_scope',
        'x': 60,
        'y': 80
    }
}
edges.append({'source': 'item_sparring_dummy', 'target': 'area_courtyard', 'type': 'in', 'properties': {}})

# 3. Explorer's Journal (carried by Explorer)
nodes['item_journal'] = {
    'id': 'item_journal',
    'type': 'item',
    'name': 'leather journal',
    'properties': {
        'name': 'leather journal',
        'description': 'a worn leather-bound journal with handwritten field notes.',
        'weight': 0.5,
        'uses': -1,
        'actions': ['examine', 'drop'],
        'tags': ['book', 'notes'],
        'world_scope_id': 'htc_scope',
        'x': 50,
        'y': 50
    }
}
edges.append({'source': 'item_journal', 'target': 'player_explorer', 'type': 'carrying', 'properties': {}})

# Players dictionary
doc_holliday_p = make_player_dict('Doc Holliday', 'player_doc_holliday')
doc_holliday_p['activity'] = {'type': 'sleeping'}

players = {
    'Explorer': make_player_dict('Explorer', 'player_explorer', known=['Courtyard', 'Great Hall'], preconceived={'known_areas': ['Courtyard', 'Great Hall']}),
    'Guard': make_player_dict('Guard', 'a1a1a1'),
    'Guard__b2b2b2': make_player_dict('Guard', 'b2b2b2'),
    'Doctor Brown': make_player_dict('Doctor Brown', 'player_doctor_brown'),
    'Doc Holliday': doc_holliday_p,
    'Crypt Ghoul': make_player_dict('Crypt Ghoul', 'player_crypt_ghoul', is_simple=True, behaviors=zombie_behaviors)
}

world_scopes = {
    'htc_scope': {
        'id': 'htc_scope',
        'name': 'HTC Fixture Scope',
        'kind': 'scope',
        'mode': 'interior',
        'grid': {'w': 4, 'h': 3},
        'area_ids': [aid for aid, _, _, _, _ in areas_def],
        'area_placements': area_placements,
        'children': [],
        'placements': {},
        'parent_id': None
    }
}

scenario = {
    '_scenario_name': 'htc_fixture',
    'schema_version': 1,
    'current_area': 'Courtyard',
    'active_player': 'Explorer',
    'narration_mode': 'concise',
    'ghost_mode': False,
    'mature_content': False,
    'time_per_tick_minutes': 1,
    'turn_number': 0,
    'world_scopes': world_scopes,
    'players': players,
    'graph': {
        'nodes': nodes,
        'edges': edges
    }
}

os.makedirs('data/scenarios', exist_ok=True)
with open('data/scenarios/htc_fixture.json', 'w', encoding='utf-8') as f:
    json.dump(scenario, f, indent=2)

print('Generated data/scenarios/htc_fixture.json successfully!')
