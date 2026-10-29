import sys
sys.stdout.reconfigure(encoding='utf-8')

for f in ['item-library.ts', 'library-browser.ts']:
    p = 'static/js/' + f
    txt = open(p, 'r', encoding='utf-8').read()
    em = '\u2014' in txt or '—' in txt
    print(f'=== {f} (em-dash: {em}, FIX: {txt.count("*FIX*")}) ===')
    for i, l in enumerate(txt.splitlines()):
        if '*FIX*' in l:
            print(f'  {i+1}: {l.strip()[:100]}')
