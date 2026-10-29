import re

# 1. item-library.ts
p = 'static/js/item-library.ts'
txt = open(p, 'r', encoding='utf-8').read()
txt = txt.replace('\u2014', ' - ').replace('—', ' - ')
txt = txt.replace('Record<string, *FIX*>', 'Record<string, unknown>')
assert '*FIX*' not in txt and '\u2014' not in txt and '—' not in txt, f"item-library.ts rem: {txt.count('*FIX*')}"
open(p, 'w', encoding='utf-8', newline='').write(txt)
print("item-library.ts clean!")

# 2. library-browser.ts
p = 'static/js/library-browser.ts'
txt = open(p, 'r', encoding='utf-8').read()
txt = txt.replace('\u2014', ' - ').replace('—', ' - ')
txt = txt.replace('no data loss on *FIX* path', 'no data loss on any path')
txt = txt.replace('let conditions: *FIX* = edgeProps.conditions', 'let conditions: Record<string, unknown> = edgeProps.conditions')
txt = txt.replace('Record<string, *FIX*>', 'Record<string, unknown>')
assert '*FIX*' not in txt and '\u2014' not in txt and '—' not in txt, f"library-browser.ts rem: {txt.count('*FIX*')}"
open(p, 'w', encoding='utf-8', newline='').write(txt)
print("library-browser.ts clean!")
