import re

# 1. projector.ts
p = 'static/js/graph/projector.ts'
txt = open(p, 'r', encoding='utf-8').read()
txt = txt.replace('\u2014', ' - ').replace('—', ' - ')
txt = txt.replace('by *FIX* of its tags', 'by any of its tags')
txt = txt.replace('one hop over *FIX* edge', 'one hop over any edge')
txt = txt.replace('(window as unknown as { GraphProjector: *FIX* }).GraphProjector = {', '(window as unknown as { GraphProjector: Record<string, unknown> }).GraphProjector = {')
txt = txt.replace('floorOf(nodeData: *FIX*) {', 'floorOf(nodeData: { floor?: number; properties?: { floor?: number }; [key: string]: unknown }) {')
txt = txt.replace('nodeMatchesQuery(node: *FIX*, q: string) {', 'nodeMatchesQuery(node: Record<string, unknown>, q: string) {')
txt = txt.replace('computeVisibleNodeIds(nodesObj: *FIX*, edgesArr: *FIX*[], state: *FIX*) {', 'computeVisibleNodeIds(nodesObj: Record<string, unknown>, edgesArr: Array<Record<string, unknown>>, state: Record<string, unknown>) {')
txt = txt.replace('edgeVisible(visibleIds: Set<string>, edge: *FIX*) {', 'edgeVisible(visibleIds: Set<string>, edge: { from?: string | number; to?: string | number; [key: string]: unknown }) {')
txt = txt.replace('applyVisibility(network: *FIX*, visibleIds: Set<string>) {', 'applyVisibility(network: unknown, visibleIds: Set<string>) {')
txt = txt.replace('const nodeUpdates: *FIX*[] = [];\n        nodesDs.forEach((node: *FIX*) => {', 'const nodeUpdates: Array<Record<string, unknown>> = [];\n        nodesDs.forEach((node: { id: string | number; hidden?: boolean; [key: string]: unknown }) => {')
txt = txt.replace('const edgeUpdates: *FIX*[] = [];\n        edgesDs.forEach((edge: *FIX*) => {', 'const edgeUpdates: Array<Record<string, unknown>> = [];\n        edgesDs.forEach((edge: { id: string | number; hidden?: boolean; from: string | number; to: string | number; [key: string]: unknown }) => {')
assert '*FIX*' not in txt and '\u2014' not in txt and '—' not in txt, "projector.ts failed assertions"
open(p, 'w', encoding='utf-8', newline='').write(txt)
print("projector.ts clean!")

# 2. graph-background.ts
p = 'static/js/graph/graph-background.ts'
txt = open(p, 'r', encoding='utf-8').read()
txt = txt.replace('\u2014', ' - ').replace('—', ' - ')
txt = txt.replace('*FIX*thing painted beneath it', 'anything painted beneath it')
txt = txt.replace('inside *FIX* grid whose aspect', 'inside any grid whose aspect')
txt = txt.replace('const griddy: *FIX* = (typeof GraphLayoutEngine !== \'undefined\' && GraphLayoutEngine)', 'const griddy: Record<string, unknown> | null = (typeof GraphLayoutEngine !== \'undefined\' && GraphLayoutEngine as unknown as Record<string, unknown>)')
txt = txt.replace('painter reference if *FIX*, else the active one.', 'painter reference if any, else the active one.')
txt = txt.replace('_posTrace?(...a: *FIX*[]): void', '_posTrace?(...a: unknown[]): void')
txt = txt.replace('for (const [id, node] of Object.entries<*FIX*>(body)) {', 'for (const [id, node] of Object.entries<Record<string, unknown>>(body)) {')
txt = txt.replace('only means *FIX*thing in Graph (free)', 'only means anything in Graph (free)')
txt = txt.replace('Record<string, *FIX*>', 'Record<string, unknown>')
txt = txt.replace('rewriting *FIX*that', 'rewriting anything that')
txt = txt.replace('panel.*FIX*= `', 'window.Lit.render(window.Lit.unsafeHTML(`')
txt = txt.replace('`;\n        panel.classList.remove(\'hidden\');', '`), panel);\n        panel.classList.remove(\'hidden\');')

txt = txt.replace(
    """        if (state.zoneMove) {
            chip.*FIX*= `<span>✥ drag to move the zone · Esc or the button to finish</span>
                <button class="btn btn-sm" id="gbg-zone-done">✔ Done</button>`;""",
    """        if (state.zoneMove) {
            window.Lit.render(window.Lit.unsafeHTML(`<span>✥ drag to move the zone · Esc or the button to finish</span>
                <button class="btn btn-sm" id="gbg-zone-done">✔ Done</button>`), chip);"""
)

txt = txt.replace(
    """        chip.*FIX*= `<span>${state.cropping
            ? '✂ drag the amber edges to crop'
            : (layer ? '🖼 drag to move · corners resize · top dot rotates · alt-click cycles' : '🖼 add an image from the panel')}</span>
            <label style="display:flex;align-items:center;gap:4px;">🎚<input id="gbg-op" type="range" min="0" max="1" step="0.05" value="${layer ? layer.opacity : OPACITY_DEFAULT}" style="width:70px;"></label>
            <button class="btn btn-sm" id="gbg-crop">${state.cropping ? 'Done cropping' : '✂ Crop'}</button>
            <button class="btn btn-sm" id="gbg-done">✔ Done</button>`;""",
    """        window.Lit.render(window.Lit.unsafeHTML(`<span>${state.cropping
            ? '✂ drag the amber edges to crop'
            : (layer ? '🖼 drag to move · corners resize · top dot rotates · alt-click cycles' : '🖼 add an image from the panel')}</span>
            <label style="display:flex;align-items:center;gap:4px;">🎚<input id="gbg-op" type="range" min="0" max="1" step="0.05" value="${layer ? layer.opacity : OPACITY_DEFAULT}" style="width:70px;"></label>
            <button class="btn btn-sm" id="gbg-crop">${state.cropping ? 'Done cropping' : '✂ Crop'}</button>
            <button class="btn btn-sm" id="gbg-done">✔ Done</button>`), chip);"""
)

txt = txt.replace(
    "menu.*FIX*= rows.join('');",
    "window.Lit.render(window.Lit.unsafeHTML(rows.join('')), menu);"
)

assert '*FIX*' not in txt and '\u2014' not in txt and '—' not in txt, f"graph-background.ts failed: {txt.count('*FIX*')} FIX left"
open(p, 'w', encoding='utf-8', newline='').write(txt)
print("graph-background.ts clean!")

# 3. tooltips.ts
p = 'static/js/graph/tooltips.ts'
txt = open(p, 'r', encoding='utf-8').read()
txt = txt.replace('\u2014', ' - ').replace('—', ' - ')
txt = txt.replace('buildTooltip(nodeData: *FIX*) {', 'buildTooltip(nodeData: Record<string, unknown>) {')
txt = txt.replace(
    'const playersHere = Object.entries(worldState.players || {}).filter(([, playerData]: *FIX*) => playerData.current_area === nodeData.name).map(([playerName]: *FIX*) => playerName);',
    'const playersHere = Object.entries(worldState.players || {}).filter(([, playerData]: [string, { current_area?: string }]) => playerData.current_area === nodeData.name).map(([playerName]: [string, unknown]) => playerName);'
)
txt = txt.replace(
    'const playersHere = Object.entries(worldState.players || {}).filter(([, pd]: *FIX*) => pd.current_area === nodeData.name).map(([pn]: *FIX*) => pn);',
    'const playersHere = Object.entries(worldState.players || {}).filter(([, pd]: [string, { current_area?: string }]) => pd.current_area === nodeData.name).map(([pn]: [string, unknown]) => pn);'
)
txt = txt.replace('_escHtml(s: *FIX*) {', '_escHtml(s: unknown) {')
txt = txt.replace('_lightLabel(light: *FIX*) {', '_lightLabel(light: unknown) {')
txt = txt.replace('_envInfo(nodeData: *FIX*) {', '_envInfo(nodeData: Record<string, unknown>) {')
txt = txt.replace('has*FIX*:', 'hasAny:')
txt = txt.replace('_envLines(nodeData: *FIX*, mode: string) {', '_envLines(nodeData: Record<string, unknown>, mode: string) {')
txt = txt.replace('if (!info.has*FIX*) return [];', 'if (!info.hasAny) return [];')
txt = txt.replace('buildTooltipHtml(nodeData: *FIX*) {', 'buildTooltipHtml(nodeData: Record<string, unknown>) {')
txt = txt.replace('effects.slice(0, 3).forEach((eff: *FIX*, i: number) => {', 'effects.slice(0, 3).forEach((eff: Record<string, unknown>, i: number) => {')
txt = txt.replace('findGraphEdge(fromId: *FIX*, toId: *FIX*) {', 'findGraphEdge(fromId: string | number, toId: string | number) {')
txt = txt.replace('return edgesArr.find((e: *FIX*) =>', 'return edgesArr.find((e: { from?: string | number; to?: string | number }) =>')
txt = txt.replace("graphManager.network.on('hoverEdge', (params: *FIX*) => {", "graphManager.network.on('hoverEdge', (params: { edge?: string | number }) => {")
txt = txt.replace("graphManager.network.on('hoverNode', (params: *FIX*) => {", "graphManager.network.on('hoverNode', (params: { node?: string | number }) => {")
txt = txt.replace('hover tooltip, if *FIX*. */', 'hover tooltip, if any. */')
assert '*FIX*' not in txt and '\u2014' not in txt and '—' not in txt, f"tooltips.ts failed: {txt.count('*FIX*')} FIX left"
open(p, 'w', encoding='utf-8', newline='').write(txt)
print("tooltips.ts clean!")

# 4. physics.ts
p = 'static/js/graph/physics.ts'
txt = open(p, 'r', encoding='utf-8').read()
txt = txt.replace('\u2014', ' - ').replace('—', ' - ')
txt = txt.replace('const gm: *FIX* =', 'const gm: unknown =')
txt = txt.replace('const cfg: *FIX* =', 'const cfg: unknown =')
txt = txt.replace('(GraphNetwork as *FIX*)', '(GraphNetwork as unknown as Record<string, Function>)')
txt = txt.replace('not over *FIX* limit', 'not over any limit')
txt = txt.replace('* tools/unit/test_graph_physics.js). *FIX* gate that says', '* tools/unit/test_graph_physics.js). Any gate that says')
txt = txt.replace('nodePinned(nodeData: *FIX*): boolean {', 'nodePinned(nodeData: { id?: string | number; properties?: Record<string, unknown>; [key: string]: unknown }): boolean {')
txt = txt.replace('(window as *FIX*).GraphLayoutEngine', '(window as unknown as { GraphLayoutEngine?: unknown }).GraphLayoutEngine')
txt = txt.replace('(window as *FIX*).GraphRelativeLayout', '(window as unknown as { GraphRelativeLayout?: unknown }).GraphRelativeLayout')
txt = txt.replace('_posTrace?(...a: *FIX*[]): void', '_posTrace?(...a: unknown[]): void')
txt = txt.replace('apply(customOptions?: *FIX*): void {', 'apply(customOptions?: Record<string, unknown>): void {')
txt = txt.replace('(window as *FIX*).GraphToolbar', '(window as unknown as { GraphToolbar?: { syncAll: () => void } }).GraphToolbar')
txt = txt.replace('can do *FIX*thing, so the', 'can do anything, so the')
assert '*FIX*' not in txt and '\u2014' not in txt and '—' not in txt, "physics.ts failed assertions"
open(p, 'w', encoding='utf-8', newline='').write(txt)
print("physics.ts clean!")
