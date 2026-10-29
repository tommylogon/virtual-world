import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

path = 'static/js/shared/trigger-graph.ts'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

orig_markers = content.count('*FIX*')
orig_emdashes = content.count('\u2014') + content.count('—')

# Specific replacements first
content = content.replace('*FIX*where', 'anywhere')
content = content.replace('*FIX*thing', 'anything')
content = content.replace('// *FIX*thing', '// Anything')
content = content.replace('Carry *FIX* such', 'Carry any such')
content = content.replace('// *FIX* other action', '// Any other action')
content = content.replace('at *FIX* pan/zoom', 'at any pan/zoom')
content = content.replace('from *FIX*where', 'from anywhere')
content = content.replace('at *FIX* zoom', 'at any zoom')
content = content.replace('Apply *FIX*way?', 'Apply anyway?')
content = content.replace('step="*FIX*"', 'step="any"')
content = content.replace("dl.*FIX*= '';", "dl.replaceChildren();")

# All remaining *FIX* are type markers -> 'any'
content = content.replace('*FIX*', 'any')

# Clean all em-dashes
content = content.replace('\u2014', '-').replace('—', '-')

new_markers = content.count('*FIX*')
new_emdashes = content.count('\u2014') + content.count('—')

with open(path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)

print(f'{path}: {orig_markers} -> {new_markers} markers, {orig_emdashes} -> {new_emdashes} em-dashes')
