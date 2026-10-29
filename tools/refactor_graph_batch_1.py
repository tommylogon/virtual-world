import re

# 1. toolbar.ts
p = 'static/js/graph/toolbar.ts'
txt = open(p, 'r', encoding='utf-8').read()
txt = txt.replace('\u2014', ' - ').replace('—', ' - ')
txt = txt.replace('assigned *FIX*where', 'assigned anywhere')
assert '*FIX*' not in txt and '\u2014' not in txt and '—' not in txt
open(p, 'w', encoding='utf-8', newline='').write(txt)
print("toolbar.ts clean!")

# 2. overlays.ts
p = 'static/js/graph/overlays.ts'
txt = open(p, 'r', encoding='utf-8').read()
txt = txt.replace('\u2014', ' - ').replace('—', ' - ')
txt = txt.replace('with *FIX* other script', 'with any other script')
assert '*FIX*' not in txt and '\u2014' not in txt and '—' not in txt
open(p, 'w', encoding='utf-8', newline='').write(txt)
print("overlays.ts clean!")

# 3. node-operations.ts
p = 'static/js/graph/node-operations.ts'
txt = open(p, 'r', encoding='utf-8').read()
txt = txt.replace('\u2014', ' - ').replace('—', ' - ')
txt = txt.replace('how m*FIX* paths', 'how many paths')
assert '*FIX*' not in txt and '\u2014' not in txt and '—' not in txt
open(p, 'w', encoding='utf-8', newline='').write(txt)
print("node-operations.ts clean!")

# 4. event-handlers.ts
p = 'static/js/graph/event-handlers.ts'
txt = open(p, 'r', encoding='utf-8').read()
txt = txt.replace('\u2014', ' - ').replace('—', ' - ')
txt = txt.replace('formData: Record<string, *FIX*>', 'formData: Record<string, unknown>')
assert '*FIX*' not in txt and '\u2014' not in txt and '—' not in txt
open(p, 'w', encoding='utf-8', newline='').write(txt)
print("event-handlers.ts clean!")

# 5. node-badges.ts
p = 'static/js/graph/node-badges.ts'
txt = open(p, 'r', encoding='utf-8').read()
txt = txt.replace('\u2014', ' - ').replace('—', ' - ')
txt = txt.replace('props: Record<string, *FIX*>', 'props: Record<string, unknown>')
txt = txt.replace('(t: *FIX*) => String(t).toLowerCase()', '(t: unknown) => String(t).toLowerCase()')
txt = txt.replace('properties?: Record<string, *FIX*>;', 'properties?: Record<string, unknown>;')
assert '*FIX*' not in txt and '\u2014' not in txt and '—' not in txt
open(p, 'w', encoding='utf-8', newline='').write(txt)
print("node-badges.ts clean!")

# 6. scope-tree.ts
p = 'static/js/graph/scope-tree.ts'
txt = open(p, 'r', encoding='utf-8').read()
txt = txt.replace('\u2014', ' - ').replace('—', ' - ')
txt = txt.replace('in *FIX* order', 'in any order')
txt = txt.replace('. *FIX* areas that belong', '. Any areas that belong')
txt = txt.replace("host.*FIX*= '';", "host.replaceChildren();")
assert '*FIX*' not in txt and '\u2014' not in txt and '—' not in txt
open(p, 'w', encoding='utf-8', newline='').write(txt)
print("scope-tree.ts clean!")
