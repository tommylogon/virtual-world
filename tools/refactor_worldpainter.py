import re

# 1. editor.ts was already written and clean

# 2. grid-model.ts
p = 'static/js/worldpainter/grid-model.ts'
txt = open(p, 'r', encoding='utf-8').read()
txt = txt.replace('\u2014', ' - ').replace('—', ' - ')

# English words & comments
txt = txt.replace('arguments stay `*FIX*` rather', 'arguments stay `any` rather')
txt = txt.replace('type GridPayload = *FIX*;', 'type GridPayload = Record<string, unknown>;')
txt = txt.replace('type Vocabulary = *FIX*;', 'type Vocabulary = Record<string, unknown> & { biomes?: Array<{ id: string; tags?: string[]; name?: string; color?: string; [key: string]: unknown }> };')
txt = txt.replace('glance; *FIX*thing else gets a', 'glance; anything else gets a')
txt = txt.replace('* *FIX*thing about `painted`.', '* anything about `painted`.')
txt = txt.replace('* How m*FIX* areas + ways', '* How many areas + ways')
txt = txt.replace('for *FIX*thing that is not a building,', 'for anything that is not a building,')
txt = txt.replace('`in` from *FIX* side that has a way.', '`in` from any side that has a way.')
txt = txt.replace('changes *FIX*thing.', 'changes anything.')

# Types & params
txt = txt.replace('function tileHeight(payload: *FIX*, x: number, y: number, vocab?: *FIX*): number {', 'function tileHeight(payload: Record<string, unknown>, x: number, y: number, vocab?: Vocabulary): number {')
txt = txt.replace('function tileObscurity(payload: *FIX*, x: number, y: number, vocab?: *FIX*): number {', 'function tileObscurity(payload: Record<string, unknown>, x: number, y: number, vocab?: Vocabulary): number {')
txt = txt.replace('function tileFloor(payload: *FIX*, x: number, y: number): number {', 'function tileFloor(payload: Record<string, unknown>, x: number, y: number): number {')

txt = txt.replace(
    """    function castSightRay(
        origin: Cell & { z?: number },
        target: Cell & { z?: number },
        payload: *FIX*,
        eyeHeight = 0.5,
        maxRange = 60,
        vocab?: *FIX*
    ): SightRayResult {""",
    """    function castSightRay(
        origin: Cell & { z?: number },
        target: Cell & { z?: number },
        payload: Record<string, unknown>,
        eyeHeight = 0.5,
        maxRange = 60,
        vocab?: Vocabulary
    ): SightRayResult {"""
)

txt = txt.replace(
    """    function computeVisibleCells(
        origin: Cell & { z?: number },
        payload: *FIX*,
        maxRange = 60,
        facing?: string | null,
        arcDegrees = 360,
        peripheralRange = 3,
        vocab?: *FIX*
    ): Set<string> {""",
    """    function computeVisibleCells(
        origin: Cell & { z?: number },
        payload: Record<string, unknown>,
        maxRange = 60,
        facing?: string | null,
        arcDegrees = 360,
        peripheralRange = 3,
        vocab?: Vocabulary
    ): Set<string> {"""
)

txt = txt.replace('function routeStats(cellCount: number, minutesPerCell?: number | null): *FIX* {', 'function routeStats(cellCount: number, minutesPerCell?: number | null): Record<string, unknown> {')
txt = txt.replace('function cellValue(payload: GridPayload, layer: string, x: number, y: number): *FIX* {', 'function cellValue(payload: GridPayload, layer: string, x: number, y: number): unknown {')
txt = txt.replace('function featureAt(payload: GridPayload, x: number, y: number): *FIX* {', 'function featureAt(payload: GridPayload, x: number, y: number): unknown {')
txt = txt.replace('function placementFor(payload: GridPayload, childId: string): *FIX* {', 'function placementFor(payload: GridPayload, childId: string): Record<string, unknown> | null {')
txt = txt.replace('return list.find((p: *FIX*) => p.id === childId) || null;', 'return list.find((p: { id: string }) => p.id === childId) || null;')
txt = txt.replace('function buildRows(payload: GridPayload): *FIX*[][] {', 'function buildRows(payload: GridPayload): Array<Array<Record<string, unknown>>> {')
txt = txt.replace('const rows: *FIX*[][] = [];', 'const rows: Array<Array<Record<string, unknown>>> = [];')
txt = txt.replace('const row: *FIX*[] = [];', 'const row: Array<Record<string, unknown>> = [];')
txt = txt.replace('const cell: Record<string, *FIX*> = {', 'const cell: Record<string, unknown> = {')
txt = txt.replace('function featureMap(payload: GridPayload): Record<string, *FIX*> {', 'function featureMap(payload: GridPayload): Record<string, unknown> {')
txt = txt.replace('const out: Record<string, *FIX*> = {};', 'const out: Record<string, unknown> = {};')
txt = txt.replace('((payload && payload.placements) || []).forEach((p: *FIX*) => {', '((payload && (payload.placements as Array<{ id: string; x: number; y: number }>)) || []).forEach((p: { id: string; x: number; y: number }) => {')
txt = txt.replace('const layers: Record<string, Record<string, *FIX*>> = {};', 'const layers: Record<string, Record<string, unknown>> = {};')
txt = txt.replace('const kept: Record<string, *FIX*> = {};', 'const kept: Record<string, unknown> = {};')
txt = txt.replace('.filter((p: *FIX*) => inBounds(p.x, p.y));', '.filter((p: { x: number; y: number }) => inBounds(p.x, p.y));')
txt = txt.replace('function estimateCompile(payload: GridPayload, regionMerge?: boolean): *FIX* {', 'function estimateCompile(payload: GridPayload, regionMerge?: boolean): Record<string, unknown> {')
txt = txt.replace('function childrenAvailable(payload: GridPayload): *FIX*[] {', 'function childrenAvailable(payload: GridPayload): Array<Record<string, unknown>> {')
txt = txt.replace('((payload && payload.children) || []).filter((c: *FIX*) => !c.placed);', '((payload && (payload.children as Array<{ placed?: boolean }>)) || []).filter((c: { placed?: boolean }) => !c.placed);')
txt = txt.replace('function areaMap(payload: GridPayload): Record<string, *FIX*> {', 'function areaMap(payload: GridPayload): Record<string, unknown> {')
txt = txt.replace('((payload && payload.area_placements) || []).forEach((a: *FIX*) => {', '((payload && (payload.area_placements as Array<{ id: string; x: number; y: number }>)) || []).forEach((a: { id: string; x: number; y: number }) => {')
txt = txt.replace('function areaAt(payload: GridPayload, x: number, y: number): *FIX* {', 'function areaAt(payload: GridPayload, x: number, y: number): Record<string, unknown> | null {')
txt = txt.replace('function areaPlacementFor(payload: GridPayload, areaId: string): *FIX* {', 'function areaPlacementFor(payload: GridPayload, areaId: string): Record<string, unknown> | null {')
txt = txt.replace('.find((a: *FIX*) => a.id === areaId) || null;', '.find((a: { id: string }) => a.id === areaId) || null;')
txt = txt.replace('function placeableAreas(payload: GridPayload, selectedId?: string): *FIX*[] {', 'function placeableAreas(payload: GridPayload, selectedId?: string): Array<Record<string, unknown>> {')
txt = txt.replace('function areaGroups(payload: GridPayload, selectedId?: string): *FIX*[] {', 'function areaGroups(payload: GridPayload, selectedId?: string): Array<{ key: string; label: string; areas: Array<Record<string, unknown>> }> {')
txt = txt.replace('const byId: Record<string, *FIX*> = {};', 'const byId: Record<string, Record<string, unknown>> = {};')
txt = txt.replace('const mine: *FIX*[] = [];', 'const mine: Array<Record<string, unknown>> = [];')
txt = txt.replace('const elsewhere: *FIX*[] = [];', 'const elsewhere: Array<Record<string, unknown>> = [];')
txt = txt.replace('candidates.forEach((a: *FIX*) => {', 'candidates.forEach((a: Record<string, unknown>) => {')
txt = txt.replace('areas: *FIX*[] }[] = [', 'areas: Array<Record<string, unknown>> }[] = [')
txt = txt.replace('(a: *FIX*) => ({ id: a.id, name: a.name, x: a.x, y: a.y, scope_id: scopeId,', '(a: Record<string, unknown>) => ({ id: a.id, name: a.name, x: a.x, y: a.y, scope_id: scopeId,')
txt = txt.replace('const known = candidates.find((a: *FIX*) => a.id === selectedId);', 'const known = candidates.find((a: Record<string, unknown>) => a.id === selectedId);')
txt = txt.replace('function cellInfo(payload: GridPayload, x: number, y: number, vocab?: Vocabulary): *FIX* {', 'function cellInfo(payload: GridPayload, x: number, y: number, vocab?: Vocabulary): Record<string, unknown> {')
txt = txt.replace('find((c: *FIX*) => c.id === childId);', 'find((c: { id: string }) => c.id === childId);')
txt = txt.replace('function cellNeighbours(payload: GridPayload, x: number, y: number, vocab?: Vocabulary): Record<string, *FIX*> {', 'function cellNeighbours(payload: GridPayload, x: number, y: number, vocab?: Vocabulary): Record<string, unknown> {')
txt = txt.replace('(payload.area_placements || []).forEach((a: *FIX*) => put(a.x, a.y));', '((payload.area_placements as Array<{ x: number; y: number }>) || []).forEach((a: { x: number; y: number }) => put(a.x, a.y));')
txt = txt.replace('(payload.placements || []).forEach((a: *FIX*) => put(a.x, a.y));', '((payload.placements as Array<{ x: number; y: number }>) || []).forEach((a: { x: number; y: number }) => put(a.x, a.y));')
txt = txt.replace('find((b: *FIX*) => b.id === biomeId);', 'find((b: { id: string }) => b.id === biomeId);')
txt = txt.replace('map((t: *FIX*) => String(t).toLowerCase());', 'map((t: unknown) => String(t).toLowerCase());')
txt = txt.replace('function cellEnter(vocab: Vocabulary, biomeId?: string | null, child?: *FIX*): string {', 'function cellEnter(vocab: Vocabulary, biomeId?: string | null, child?: Record<string, unknown>): string {')
txt = txt.replace('((payload.area_placements) || []).forEach((a: *FIX*) => {', '((payload.area_placements as Array<{ x: number; y: number }>) || []).forEach((a: { x: number; y: number }) => {')
txt = txt.replace('((payload.placements) || []).forEach((a: *FIX*) => {', '((payload.placements as Array<{ x: number; y: number }>) || []).forEach((a: { x: number; y: number }) => {')
txt = txt.replace('function isWaterCell(payload: *FIX*, x: number, y: number, vocab?: *FIX*): boolean {', 'function isWaterCell(payload: Record<string, unknown>, x: number, y: number, vocab?: Vocabulary): boolean {')
txt = txt.replace('const b = vocab.biomes.find((v: *FIX*) => v.id === bId);', 'const b = (vocab.biomes || []).find((v: { id: string }) => v.id === bId);')
txt = txt.replace('function deriveWaterCurrent(payload: *FIX*, x: number, y: number, vocab?: *FIX*): *FIX* {', 'function deriveWaterCurrent(payload: Record<string, unknown>, x: number, y: number, vocab?: Vocabulary): Record<string, unknown> {')
txt = txt.replace('let manual: *FIX* = null;', 'let manual: unknown = null;')
txt = txt.replace('find((v: *FIX*) => v.id === bId);', 'find((v: { id: string }) => v.id === bId);')

rem = txt.count('*FIX*')
print(f"Remaining in grid-model.ts: {rem}")
if rem > 0:
    for i, l in enumerate(txt.splitlines()):
        if '*FIX*' in l:
            print(f"  {i+1}: {l.strip()[:100]}")
assert rem == 0, f"grid-model.ts rem: {rem}"
assert '\u2014' not in txt and '—' not in txt, "Em-dash in grid-model.ts"
open(p, 'w', encoding='utf-8', newline='').write(txt)
print("grid-model.ts 100% clean!")
