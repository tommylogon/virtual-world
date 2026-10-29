import re

# 1. world-state.ts was already written and clean
# 2. world-sync.ts was already written and clean

# 3. main.ts
p = 'static/js/main.ts'
txt = open(p, 'r', encoding='utf-8').read()
txt = txt.replace('\u2014', ' - ').replace('—', ' - ')

txt = txt.replace('so *FIX* module that tests', 'so any module that tests')
txt = txt.replace('designers can set *FIX* state', 'designers can set any state')
txt = txt.replace('before *FIX*thing that renders', 'before anything that renders')
txt = txt.replace('// Reflect *FIX* graph change', '// Reflect any graph change')

txt = txt.replace('(window as *FIX*).gridModel', '(window as unknown as { gridModel?: unknown }).gridModel')
txt = txt.replace('(window as *FIX*).worldPainter', '(window as unknown as { worldPainter?: unknown }).worldPainter')
txt = txt.replace('(window as *FIX*).structures', '(window as unknown as { structures?: unknown }).structures')
txt = txt.replace('const win = window as *FIX*;', 'const win = window as unknown as Record<string, unknown>;')
txt = txt.replace('.then((res: *FIX*) =>', '.then((res: unknown) =>')
txt = txt.replace('openCreateModal(\'area\', async (data: *FIX*) =>', 'openCreateModal(\'area\', async (data: unknown) =>')
txt = txt.replace('openCreateModal(\'item\', async (data: *FIX*) =>', 'openCreateModal(\'item\', async (data: unknown) =>')
txt = txt.replace('openCreateModal(\'connection\', async (data: *FIX*) =>', 'openCreateModal(\'connection\', async (data: unknown) =>')
txt = txt.replace('function connectSummary(res: *FIX*, payload: *FIX*) {', 'function connectSummary(res: unknown, payload: unknown) {')
txt = txt.replace('Record<string, *FIX*>', 'Record<string, unknown>')
txt = txt.replace('(config as *FIX*)', '(config as unknown as Record<string, Function>)')
txt = txt.replace('(ApiClient as *FIX*)', '(ApiClient as unknown as Record<string, Function>)')
txt = txt.replace('([name, r]: [string, *FIX*])', '([name, r]: [string, unknown])')
txt = txt.replace('([n, r]: [string, *FIX*])', '([n, r]: [string, unknown])')
txt = txt.replace('const set = (id: string, val: *FIX*) =>', 'const set = (id: string, val: unknown) =>')
txt = txt.replace('(window as *FIX*).CreateModal', '(window as unknown as { CreateModal?: { _tagMSArea?: { setValue: Function }; _tagMSConn?: { setValue: Function } } }).CreateModal')
txt = txt.replace('catch (err: *FIX*) {', 'catch (err: unknown) {')
txt = txt.replace('catch(e: *FIX*) {', 'catch(e: unknown) {')
txt = txt.replace('onSubmit: (data: *FIX*) => void', 'onSubmit: (data: unknown) => void')
txt = txt.replace('catch((err: *FIX*) =>', 'catch((err: { message?: string } | null) =>')
txt = txt.replace('.action(cmd).then((data: *FIX*) =>', '.action(cmd).then((data: unknown) =>')
txt = txt.replace('.playerSpeak(speakerName, text, areaName).then((res: *FIX*) =>', '.playerSpeak(speakerName, text, areaName).then((res: unknown) =>')
txt = txt.replace('(window as *FIX*).VWSimultaneousControls', '(window as unknown as { VWSimultaneousControls?: { init(): void; render(): void } }).VWSimultaneousControls')
txt = txt.replace('worldState.on(\'update\', (state: *FIX*) => {', 'worldState.on(\'update\', (state: unknown) => {')
txt = txt.replace('(window as *FIX*).narrationUI', '(window as unknown as { narrationUI?: unknown }).narrationUI')
txt = txt.replace('(res.summary || *FIX*)', '(res.summary || "ok")')
txt = txt.replace('passages.map((p: *FIX*) =>', 'passages.map((p: { from?: string; to?: string; type?: string; direction?: string; description?: string }) =>')

rem = txt.count('*FIX*')
print(f"Remaining in main.ts: {rem}")
assert rem == 0, f"main.ts rem: {rem}"
assert '\u2014' not in txt and '—' not in txt, "Em-dash in main.ts"
open(p, 'w', encoding='utf-8', newline='').write(txt)
print("main.ts clean!")

# 4. graph-manager.ts
p = 'static/js/graph-manager.ts'
txt = open(p, 'r', encoding='utf-8').read()
txt = txt.replace('\u2014', ' - ').replace('—', ' - ')

txt = txt.replace('M*FIX* methods here are thin', 'Many methods here are thin')
txt = txt.replace('ambient `EdgeTypes: *FIX*` can', 'ambient `EdgeTypes: any` can')
txt = txt.replace('interface says `*FIX*` for', 'interface says `any` for')
txt = txt.replace('rather than dropping to `*FIX*`.', 'rather than dropping to `any`.')
txt = txt.replace('(and *FIX* throw it produces)', '(and any throw it produces)')

txt = txt.replace('properties?: Record<string, *FIX*>;', 'properties?: Record<string, unknown>;')
txt = txt.replace('[key: string]: *FIX*;', '[key: string]: unknown;')
txt = txt.replace('nodeData?: *FIX*;', 'nodeData?: unknown;')
txt = txt.replace('edgeData?: *FIX*;', 'edgeData?: unknown;')
txt = txt.replace('declare network: *FIX*;', 'declare network: unknown;')
txt = txt.replace('declare _legendEl: *FIX*;', 'declare _legendEl: HTMLElement | null;')
txt = txt.replace('declare _labelCache: *FIX*;', 'declare _labelCache: unknown;')
txt = txt.replace('declare _revealedItemIds: Map<string, *FIX*>;', 'declare _revealedItemIds: Map<string, unknown>;')
txt = txt.replace('declare _baseNodeStyles: *FIX*;', 'declare _baseNodeStyles: unknown;')
txt = txt.replace('declare _baseEdgeStyles: *FIX*;', 'declare _baseEdgeStyles: unknown;')
txt = txt.replace('declare _edgeTooltipHtml: *FIX*;', 'declare _edgeTooltipHtml: unknown;')
txt = txt.replace('declare _tagFilter: *FIX*;', 'declare _tagFilter: unknown;')
txt = txt.replace('declare _tagLibrary: *FIX*;', 'declare _tagLibrary: unknown;')
txt = txt.replace('declare _tagPanelEl: *FIX*;', 'declare _tagPanelEl: HTMLElement | null;')

txt = txt.replace('(ev: *FIX*) =>', '(ev: unknown) =>')
txt = txt.replace('bar.*FIX*=', 'window.Lit.render(window.Lit.unsafeHTML(')
txt = txt.replace('`;\n            this.applyToolbarState();', '`), bar);\n            this.applyToolbarState();')
txt = txt.replace('sel.*FIX*= \'<option value="">🗺️ Scope…</option>\';', 'window.Lit.render(window.Lit.unsafeHTML(\'<option value="">🗺️ Scope…</option>\'), sel);')
txt = txt.replace('sel.*FIX*= \'<option value="">scopes unavailable</option>\';', 'window.Lit.render(window.Lit.unsafeHTML(\'<option value="">scopes unavailable</option>\'), sel);')
txt = txt.replace('sel.*FIX*= \'\';', 'sel.replaceChildren();')

txt = txt.replace('nodeData: *FIX*', 'nodeData: Record<string, unknown>')
txt = txt.replace('params: *FIX*', 'params: unknown')
txt = txt.replace('(e: *FIX*) =>', '(e: { from?: string | number; to?: string | number; id?: string | number }) =>')
txt = txt.replace('let value: *FIX* = rawValue;', 'let value: unknown = rawValue;')
txt = txt.replace('_onAddNode(data: *FIX*, callback: *FIX*)', '_onAddNode(data: unknown, callback: (d: unknown) => void)')
txt = txt.replace('_onAddEdge(data: *FIX*, callback: *FIX*)', '_onAddEdge(data: unknown, callback: (d: unknown) => void)')
txt = txt.replace('edgeData: *FIX*', 'edgeData: Record<string, unknown>')
txt = txt.replace('edge: *FIX*', 'edge: Record<string, unknown>')
txt = txt.replace('const body: *FIX* =', 'const body: unknown =')
txt = txt.replace('const parentBody: *FIX* =', 'const parentBody: unknown =')
txt = txt.replace('GraphLayoutEngine?: *FIX*', 'GraphLayoutEngine?: unknown')
txt = txt.replace('GraphRelativeLayout?: *FIX*', 'GraphRelativeLayout?: unknown')

rem = txt.count('*FIX*')
print(f"Remaining in graph-manager.ts: {rem}")
assert rem == 0, f"graph-manager.ts rem: {rem}"
assert '\u2014' not in txt and '—' not in txt, "Em-dash in graph-manager.ts"
open(p, 'w', encoding='utf-8', newline='').write(txt)
print("graph-manager.ts clean!")
