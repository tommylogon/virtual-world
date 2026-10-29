import re

# 1. focus.ts
p = 'static/js/graph/focus.ts'
txt = open(p, 'r', encoding='utf-8').read()
txt = txt.replace('\u2014', ' - ').replace('—', ' - ')
txt = txt.replace('instead of `*FIX*`', 'instead of `any`')
txt = txt.replace('restores *FIX* parked physics', 'restores any parked physics')
txt = txt.replace('means *FIX*thing while matches', 'means anything while matches')
txt = txt.replace('nodesDs.forEach((node: *FIX*) => {', 'nodesDs.forEach((node: { id: string | number; hidden?: boolean; physics?: boolean; [key: string]: unknown }) => {')
txt = txt.replace('& *FIX* parked physics after', '& any parked physics after')
assert '*FIX*' not in txt and '\u2014' not in txt and '—' not in txt
open(p, 'w', encoding='utf-8', newline='').write(txt)
print("focus.ts clean!")

# 2. separation.ts
p = 'static/js/graph/separation.ts'
txt = open(p, 'r', encoding='utf-8').read()
txt = txt.replace('\u2014', ' - ').replace('—', ' - ')
txt = txt.replace('joined by *FIX* edge is exempt', 'joined by any edge is exempt')
txt = txt.replace('/** A graph edge; *FIX* type exempts', '/** A graph edge; any type exempts')
txt = txt.replace('(*FIX* type exempts its pair)', '(any type exempts its pair)')
txt = txt.replace('let *FIX* = false;', 'let any = false;')
txt = txt.replace('*FIX* = true;', 'any = true;')
txt = txt.replace('if (!*FIX*) break;', 'if (!any) break;')
assert '*FIX*' not in txt and '\u2014' not in txt and '—' not in txt
open(p, 'w', encoding='utf-8', newline='').write(txt)
print("separation.ts clean!")

# 3. tree-view.ts
p = 'static/js/graph/tree-view.ts'
txt = open(p, 'r', encoding='utf-8').read()
txt = txt.replace('\u2014', ' - ').replace('—', ' - ')
txt = txt.replace('bare consts (*FIX*)', 'bare consts (any)')
txt = txt.replace('with *FIX* other script declaring', 'with any other script declaring')
txt = txt.replace('(worldState as *FIX*).getNodeByIdentifier?.(areaName)', '(worldState as unknown as { getNodeByIdentifier?: (id: string) => { properties?: Record<string, unknown>; [key: string]: unknown } | null }).getNodeByIdentifier?.(areaName)')
txt = txt.replace('(worldState as *FIX*).getNodeByIdentifier?.(name)', '(worldState as unknown as { getNodeByIdentifier?: (id: string) => { properties?: Record<string, unknown>; [key: string]: unknown } | null }).getNodeByIdentifier?.(name)')
txt = txt.replace('|| (area as *FIX*).world_scope_id', '|| (area as { world_scope_id?: string; scope_id?: string }).world_scope_id')
txt = txt.replace('which scope *FIX* of it was in', 'which scope any of it was in')
assert '*FIX*' not in txt and '\u2014' not in txt and '—' not in txt
open(p, 'w', encoding='utf-8', newline='').write(txt)
print("tree-view.ts clean!")

# 4. graph-export.ts
p = 'static/js/graph/graph-export.ts'
txt = open(p, 'r', encoding='utf-8').read()
txt = txt.replace('\u2014', ' - ').replace('—', ' - ')
txt = txt.replace('const nodes: *FIX*[] = [];', 'const nodes: Array<Record<string, unknown>> = [];')
txt = txt.replace('data.nodes.get().forEach((node: *FIX*) => {', 'data.nodes.get().forEach((node: Record<string, unknown>) => {')
txt = txt.replace('const edges: *FIX*[] = [];', 'const edges: Array<Record<string, unknown>> = [];')
txt = txt.replace('data.edges.get().forEach((edge: *FIX*) => {', 'data.edges.get().forEach((edge: Record<string, unknown>) => {')
txt = txt.replace('function _preloadImages(nodes: *FIX*[]): Promise<void[]> {', 'function _preloadImages(nodes: Array<Record<string, unknown>>): Promise<void[]> {')
txt = txt.replace('nodes.forEach((node: *FIX*) => {', 'nodes.forEach((node: Record<string, unknown>) => {')
txt = txt.replace('Record<string, *FIX*>', 'Record<string, unknown>')
txt = txt.replace('nodes: { get(): *FIX*[] }; edges: { get(): *FIX*[] }', 'nodes: { get(): Array<Record<string, unknown>> }; edges: { get(): Array<Record<string, unknown>> }')
assert '*FIX*' not in txt and '\u2014' not in txt and '—' not in txt
open(p, 'w', encoding='utf-8', newline='').write(txt)
print("graph-export.ts clean!")

# 5. relative-layout.ts
p = 'static/js/graph/relative-layout.ts'
txt = open(p, 'r', encoding='utf-8').read()
txt = txt.replace('\u2014', ' - ').replace('—', ' - ')
txt = txt.replace('before *FIX* per-parent override', 'before any per-parent override')
txt = txt.replace('however m*FIX* things are in there', 'however many things are in there')
txt = txt.replace('and *FIX*thing with no relation', 'and anything with no relation')
txt = txt.replace('Restore *FIX* displaced node to', 'Restore any displaced node to')
txt = txt.replace('how m*FIX* nodes were placed', 'how many nodes were placed')
txt = txt.replace('how m*FIX* nodes moved', 'how many nodes moved')
txt = txt.replace('fires again on *FIX* mid-life', 'fires again on any mid-life')
txt = txt.replace('_posTrace?(...a: *FIX*[]): void', '_posTrace?(...a: unknown[]): void')
assert '*FIX*' not in txt and '\u2014' not in txt and '—' not in txt
open(p, 'w', encoding='utf-8', newline='').write(txt)
print("relative-layout.ts clean!")
