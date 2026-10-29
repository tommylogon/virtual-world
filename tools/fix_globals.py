import sys

sys.stdout.reconfigure(encoding='utf-8')

path = 'static/js/types/globals.d.ts'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

orig_markers = content.count('*FIX*')

content = content.replace('*FIX*one', 'anyone')
content = content.replace('*FIX*thing', 'anything')
content = content.replace('*FIX*', 'any')
content = content.replace('\u2014', '-').replace('—', '-')

new_markers = content.count('*FIX*')
with open(path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)

print(f'{path}: {orig_markers} -> {new_markers} markers')
