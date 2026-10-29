import sys

# soak-api.ts
p = 'static/js/soak/soak-api.ts'
txt = open(p, 'r', encoding='utf-8').read()
txt = txt.replace('\u2014', ' - ').replace('—', ' - ')
txt = txt.replace('Promise<*FIX*>', 'Promise<unknown>')
txt = txt.replace('let body: *FIX* = null;', 'let body: unknown = null;')
assert '\u2014' not in txt and '—' not in txt
rem = txt.count('*FIX*')
assert rem == 0, f"Remaining in soak-api.ts: {rem}"
open(p, 'w', encoding='utf-8', newline='').write(txt)
print("soak-api.ts clean!")

# soak-spacetime.ts
p = 'static/js/soak/soak-spacetime.ts'
txt = open(p, 'r', encoding='utf-8').read()
txt = txt.replace('\u2014', ' - ').replace('—', ' - ')
txt = txt.replace('without dropping *FIX*one', 'without dropping anyone')
txt = txt.replace('error *FIX*where', 'error anywhere')
assert '\u2014' not in txt and '—' not in txt
rem = txt.count('*FIX*')
assert rem == 0, f"Remaining in soak-spacetime.ts: {rem}"
open(p, 'w', encoding='utf-8', newline='').write(txt)
print("soak-spacetime.ts clean!")
