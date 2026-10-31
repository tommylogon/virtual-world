import json
import re
import os

with open('data/exports/full_user_goals_step_1014.txt', 'r', encoding='utf-8') as f:
    raw = f.read()

# Replace any em-dash or smart dash with a plain hyphen
raw = raw.replace('\u2014', '-').replace('\u2013', '-').replace('-', '-').replace('–', '-')
raw = raw.replace('\u2018', "'").replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"')

# Clean leading prompt text if any
if 'Here are the 10 example gimps' in raw:
    idx = raw.find('# 1. ZOE MERCER')
    if idx != -1:
        raw = raw[idx:]

os.makedirs('data/library/character_goals', exist_ok=True)

# Parse into structured dictionary
characters = {}
current_char = None
current_goal = None

lines = raw.split('\n')
for line in lines:
    line_clean = line.strip()
    m_char = re.match(r'^#\s*\d+\.\s*(.+)', line_clean)
    if m_char:
        current_char = m_char.group(1).strip()
        characters[current_char] = []
        current_goal = None
        continue
    
    m_goal = re.match(r'^###\s*Goal\s*(\d+):\s*(.+)', line_clean)
    if m_goal and current_char:
        current_goal = {
            'goal_number': int(m_goal.group(1)),
            'title': m_goal.group(2).strip(),
            'G': '',
            'I': '',
            'M': '',
            'P': ''
        }
        characters[current_char].append(current_goal)
        continue
    
    if current_goal:
        m_g = re.match(r'^\*\s*\*\*G\s*\(Goal\):\*\*\s*(.+)', line_clean)
        if m_g:
            current_goal['G'] = m_g.group(1).strip()
            continue
        m_i = re.match(r'^\*\s*\*\*I\s*\(Intention\):\*\*\s*(.+)', line_clean)
        if m_i:
            current_goal['I'] = m_i.group(1).strip()
            continue
        m_m = re.match(r'^\*\s*\*\*M\s*\(Motivation\):\*\*\s*(.+)', line_clean)
        if m_m:
            current_goal['M'] = m_m.group(1).strip()
            continue
        m_p = re.match(r'^\*\s*\*\*P\s*\(Pursuit\):\*\*\s*(.+)', line_clean)
        if m_p:
            current_goal['P'] = m_p.group(1).strip()
            continue

with open('data/library/character_goals/millwood_arcs.json', 'w', encoding='utf-8') as f:
    json.dump(characters, f, indent=2, ensure_ascii=False)

md_content = """---
type: doc
tags: [scenario/millwood, characters, gimp, goals]
---

# Millwood Ensemble: Character GIMP Arcs

The following 60 GIMP goals define the personal stakes, domestic pressures, and tangible pursuits for the core Millwood ensemble.

""" + raw

with open('docs/scenarios/millwood-character-goals.md', 'w', encoding='utf-8') as f:
    f.write(md_content)

print(f"Saved JSON with {len(characters)} characters. Total goals: {sum(len(v) for v in characters.values())}")
