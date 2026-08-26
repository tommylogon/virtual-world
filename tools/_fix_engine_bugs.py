"""Fix engine module bugs where subsystem instances are called as functions."""
import re

# Fix ghost.py - already done manually, verify
with open('engine/ghost.py') as f:
    ghost = f.read()
assert 'self.skills.players.get' in ghost, 'ghost.py not fixed'
assert 'self.logging_events.add_log_entry' in ghost, 'ghost.py logging not fixed'

# Fix item_actions.py
with open('engine/item_actions.py') as f:
    content = f.read()

replacements = [
    ('self.ghost_system(player_manager, "take", item_name)',
     'self.ghost_system.check_ghost_action(player_manager, "take", item_name)'),
    ('self.ghost_system(player_manager, "drop", item_name)',
     'self.ghost_system.check_ghost_action(player_manager, "drop", item_name)'),
    ('self.ghost_system(player_manager, action_verb, item_name)',
     'self.ghost_system.check_ghost_action(player_manager, action_verb, item_name)'),
    ('self.ghost_system(player_manager, "use", item_name)',
     'self.ghost_system.check_ghost_action(player_manager, "use", item_name)'),
    ('self.npc_behaviors("on_item_taken", {"target_item": item_name})',
     'self.npc_behaviors.process_simple_npcs("on_item_taken", {"target_item": item_name})'),
]

for old, new in replacements:
    count = content.count(old)
    if count > 0:
        content = content.replace(old, new)
        print(f'Fixed {count}x: {old[:60]}...')
    else:
        print(f'NOT FOUND: {old[:60]}...')

with open('engine/item_actions.py', 'w') as f:
    f.write(content)

# Fix narration.py
with open('engine/narration.py') as f:
    content = f.read()

content = content.replace(
    'self.npc_behaviors(\n                "on_speech_heard", {"speaker": speaker_name, "speech": speech_text, "area": area_name}\n            )',
    'self.npc_behaviors.process_simple_npcs("on_speech_heard", {"speaker": speaker_name, "speech": speech_text, "area": area_name})'
)

with open('engine/narration.py', 'w') as f:
    f.write(content)
print('narration.py fixed')

# Fix area_description.py
with open('engine/area_description.py') as f:
    content = f.read()

if 'self.item_actions(' in content:
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'self.item_actions(' in line:
            print(f'area_description.py line {i+1}: {line.strip()}')
    content = content.replace(
        'self.item_actions("look", player=self.player_manager.player)',
        'self.item_actions.get_item_desc("look", player=self.player_manager.player)'
    )

with open('engine/area_description.py', 'w') as f:
    f.write(content)
print('area_description.py fixed')

# Fix tick_manager.py
with open('engine/tick_manager.py') as f:
    content = f.read()

content = content.replace(
    'self.npc_behaviors()',
    'self.npc_behaviors.process_simple_npcs()'
)

with open('engine/tick_manager.py', 'w') as f:
    f.write(content)
print('tick_manager.py fixed')

print('\nAll fixes applied.')

