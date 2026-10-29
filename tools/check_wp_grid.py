import sys
sys.stdout.reconfigure(encoding='utf-8')

p = 'static/js/worldpainter/grid-model.ts'
txt = open(p, 'r', encoding='utf-8').read()
em = '\u2014' in txt or '—' in txt
print(f'=== grid-model.ts (em-dash: {em}, FIX: {txt.count("*FIX*")}) ===')
for i, l in enumerate(txt.splitlines()):
    if '*FIX*' in l:
        print(f'{i+1}: {l.strip()[:100]}')
