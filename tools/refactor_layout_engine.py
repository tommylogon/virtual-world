import re

p = 'static/js/graph/layout-engine.ts'
txt = open(p, 'r', encoding='utf-8').read()

txt = txt.replace('\u2014', ' - ').replace('—', ' - ')

# Comments & English words
txt = txt.replace('at *FIX* pitch.', 'at any pitch.')
txt = txt.replace('and *FIX* other viewer that', 'and any other viewer that')
txt = txt.replace('tested at *FIX* pitch.', 'tested at any pitch.')
txt = txt.replace('like *FIX* dragged', 'like any dragged')
txt = txt.replace('held by **FIX*thing*', 'held by *anything*')
txt = txt.replace('like *FIX* other node (task-530).', 'like any other node (task-530).')
txt = txt.replace('hit *FIX* imported world rather', 'hit any imported world rather')
txt = txt.replace('`*FIX*` matches what main', '`any` matches what main')

# Boolean 'any' variable in paintedFrame
txt = txt.replace(
    'let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity, *FIX* = false;',
    'let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity, any = false;'
)
txt = txt.replace('*FIX* = true;', 'any = true;')
txt = txt.replace('return *FIX* ? { minX, minY, maxX, maxY } : null;', 'return any ? { minX, minY, maxX, maxY } : null;')

# Types
txt = txt.replace('Record<string, *FIX*>', 'Record<string, unknown>')
txt = txt.replace('Object.entries<*FIX*>', 'Object.entries<Record<string, unknown>>')
txt = txt.replace('Object.values<*FIX*>', 'Object.values<Record<string, unknown>>')
txt = txt.replace('rooms: Record<string, *FIX*>', 'rooms: Record<string, { exits?: Record<string, { to?: string }> }>')
txt = txt.replace('exits: Record<string, *FIX*>', 'exits: Record<string, { to?: string }>')
txt = txt.replace('[direction, exitData]: [string, *FIX*]', '[direction, exitData]: [string, { to?: string }]')
txt = txt.replace('const areaUpdates: *FIX*[] = [];', 'const areaUpdates: Array<{ id: string | number; x: number; y: number; physics?: boolean }> = [];')
txt = txt.replace('const wayUpdates: *FIX*[] = [];', 'const wayUpdates: Array<{ id: string | number; x: number; y: number; physics?: boolean }> = [];')
txt = txt.replace('const looseUpdates: *FIX*[] = [];', 'const looseUpdates: Array<{ id: string | number; x: number; y: number; physics?: boolean }> = [];')
txt = txt.replace('const connectedRooms: *FIX*[] = [];', 'const connectedRooms: string[] = [];')
txt = txt.replace('(e: *FIX*) => e.type === \'connection\'', '(e: { type?: string; from?: string; to?: string }) => e.type === \'connection\'')
txt = txt.replace('(edge: *FIX*) => {', '(edge: { from?: string; to?: string }) => {')
txt = txt.replace('as *FIX*[];', 'as Array<{ from?: string; to?: string; type?: string }>;')
txt = txt.replace('filter((u: *FIX*) => u && !frozen(u.id))', 'filter((u: { id?: string | number } | null | undefined) => u && !frozen(u.id))')
txt = txt.replace('{ network?: *FIX* }', '{ network?: unknown }')
txt = txt.replace('gridPosition(cell: *FIX*, pitch?: number) {', 'gridPosition(cell: [number, number] | { x: number; y: number }, pitch?: number) {')
txt = txt.replace('seedFor(nodeData: *FIX*, frame?: { minX: number; minY: number; maxX: number; maxY: number } | null)', 'seedFor(nodeData: Record<string, unknown>, frame?: { minX: number; minY: number; maxX: number; maxY: number } | null)')
txt = txt.replace('nodeScopeId(node: *FIX*) {', 'nodeScopeId(node: Record<string, unknown>) {')
txt = txt.replace('offsetPxFor(node: *FIX*, offsets?:', 'offsetPxFor(node: Record<string, unknown>, offsets?:')
txt = txt.replace('scopedGridPosition(properties: *FIX*, node: *FIX*, offsets?:', 'scopedGridPosition(properties: Record<string, unknown>, node: Record<string, unknown>, offsets?:')
txt = txt.replace('isFrozen(node: *FIX*) {', 'isFrozen(node: { id?: string | number; properties?: Record<string, unknown>; [key: string]: unknown }) {')
txt = txt.replace('_gridUpdates(nodesObj: Record<string, unknown>, nodesDS: *FIX*, offsets?:', '_gridUpdates(nodesObj: Record<string, unknown>, nodesDS: unknown, offsets?:')
txt = txt.replace('const updates: *FIX*[] = [];', 'const updates: Array<{ id: string | number; x: number; y: number; physics?: boolean }> = [];')
txt = txt.replace('as *FIX*[])', 'as Array<{ from?: string; to?: string; type?: string }>)')
txt = txt.replace('_posTrace?(...a: *FIX*[]): void', '_posTrace?(...a: unknown[]): void')
txt = txt.replace('hasPaintedCoords(properties: *FIX*) {', 'hasPaintedCoords(properties: Record<string, unknown> | null | undefined) {')
txt = txt.replace('_applyGridLayout(nodesObj: Record<string, unknown>, nodesDS: *FIX*, offsets?:', '_applyGridLayout(nodesObj: Record<string, unknown>, nodesDS: unknown, offsets?:')
txt = txt.replace('const fitOpts: *FIX* = { animation: false };', 'const fitOpts: Record<string, unknown> = { animation: false };')
txt = txt.replace('GraphLayoutEngine: *FIX*;', 'GraphLayoutEngine: typeof GraphLayoutEngine;')

rem = txt.count('*FIX*')
print(f"Remaining in layout-engine.ts: {rem}")
if rem > 0:
    for i, l in enumerate(txt.splitlines()):
        if '*FIX*' in l:
            print(f"  {i+1}: {l.strip()[:100]}")
assert rem == 0, f"Remaining in layout-engine.ts: {rem}"
assert '\u2014' not in txt and '—' not in txt, "Em-dash in layout-engine.ts"
open(p, 'w', encoding='utf-8', newline='').write(txt)
print("layout-engine.ts 100% clean!")
