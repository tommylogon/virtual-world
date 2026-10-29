import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

def replace_em_dashes(text: str) -> str:
    return text.replace('\u2014', '-').replace('—', '-')

def fix_file(path: str, transformer):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    orig_markers = content.count('*FIX*')
    new_content = transformer(content)
    new_content = replace_em_dashes(new_content)
    new_markers = new_content.count('*FIX*')
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(new_content)
    print(f'{path}: {orig_markers} -> {new_markers} markers (em-dashes cleaned)')

# 1. storage.ts (17)
def fix_storage(s: str) -> str:
    s = s.replace('async get(storeName: string, key: string): Promise<*FIX*> {', 'async get(storeName: string, key: string): Promise<unknown> {')
    s = s.replace('return new Promise<*FIX*>((resolve) => {\n            try {\n                const tx = this._db!.transaction(storeName, \'readonly\');',
                  'return new Promise<unknown>((resolve) => {\n            try {\n                const tx = this._db!.transaction(storeName, \'readonly\');')
    s = s.replace('async set(storeName: string, key: string, value: unknown): Promise<*FIX*> {', 'async set(storeName: string, key: string, value: unknown): Promise<boolean> {')
    s = s.replace('return new Promise<*FIX*>((resolve) => {\n            try {\n                const tx = this._db!.transaction(storeName, \'readwrite\');\n                const store = tx.objectStore(storeName);\n                store.put',
                  'return new Promise<boolean>((resolve) => {\n            try {\n                const tx = this._db!.transaction(storeName, \'readwrite\');\n                const store = tx.objectStore(storeName);\n                store.put')
    s = s.replace('async delete(storeName: string, key: string): Promise<*FIX*> {', 'async delete(storeName: string, key: string): Promise<boolean> {')
    s = s.replace('return new Promise<*FIX*>((resolve) => {\n            try {\n                const tx = this._db!.transaction(storeName, \'readwrite\');\n                const store = tx.objectStore(storeName);\n                store.delete',
                  'return new Promise<boolean>((resolve) => {\n            try {\n                const tx = this._db!.transaction(storeName, \'readwrite\');\n                const store = tx.objectStore(storeName);\n                store.delete')
    s = s.replace('async getAll(storeName: string): Promise<*FIX*> {', 'async getAll(storeName: string): Promise<Record<string, unknown>> {')
    s = s.replace('return new Promise<*FIX*>((resolve) => {\n            try {\n                const tx = this._db!.transaction(storeName, \'readonly\');\n                const store = tx.objectStore(storeName);\n                const req = store.getAll();\n                req.onsuccess = () => {\n                    const items = req.result || [];\n                    const map: Record<string, unknown> = {};\n                    items.forEach((item: *FIX*) =>',
                  'return new Promise<Record<string, unknown>>((resolve) => {\n            try {\n                const tx = this._db!.transaction(storeName, \'readonly\');\n                const store = tx.objectStore(storeName);\n                const req = store.getAll();\n                req.onsuccess = () => {\n                    const items = req.result || [];\n                    const map: Record<string, unknown> = {};\n                    items.forEach((item: { key: string; value: unknown }) =>')
    s = s.replace('async getAllAsArray(storeName: string): Promise<*FIX*> {', 'async getAllAsArray(storeName: string): Promise<unknown[]> {')
    s = s.replace('return new Promise<*FIX*>((resolve) => {\n            try {\n                const tx = this._db!.transaction(storeName, \'readonly\');\n                const store = tx.objectStore(storeName);\n                const req = store.getAll();\n                req.onsuccess = () => resolve(req.result || []);',
                  'return new Promise<unknown[]>((resolve) => {\n            try {\n                const tx = this._db!.transaction(storeName, \'readonly\');\n                const store = tx.objectStore(storeName);\n                const req = store.getAll();\n                req.onsuccess = () => resolve(req.result || []);')
    s = s.replace('async clear(storeName: string): Promise<*FIX*> {', 'async clear(storeName: string): Promise<boolean> {')
    s = s.replace('return new Promise<*FIX*>((resolve) => {\n            try {\n                const tx = this._db!.transaction(storeName, \'readwrite\');\n                const store = tx.objectStore(storeName);\n                store.clear();',
                  'return new Promise<boolean>((resolve) => {\n            try {\n                const tx = this._db!.transaction(storeName, \'readwrite\');\n                const store = tx.objectStore(storeName);\n                store.clear();')
    s = s.replace('async saveEventLog(entries: string[]): Promise<*FIX*> {', 'async saveEventLog(entries: string[]): Promise<boolean> {')
    s = s.replace('return new Promise<*FIX*>((resolve) => {\n            if (!this._db) { resolve(false); return; }',
                  'return new Promise<boolean>((resolve) => {\n            if (!this._db) { resolve(false); return; }')
    s = s.replace('async loadEventLog(): Promise<*FIX*> {', 'async loadEventLog(): Promise<unknown[]> {')
    s = s.replace('return new Promise<*FIX*>((resolve) => {\n            if (!this._db) { resolve([]); return; }',
                  'return new Promise<unknown[]>((resolve) => {\n            if (!this._db) { resolve([]); return; }')
    # fallback replacements for any missed
    s = s.replace('Promise<*FIX*>', 'Promise<unknown>')
    s = s.replace('(item: *FIX*)', '(item: { key: string; value: unknown })')
    return s
fix_file('static/js/storage.ts', fix_storage)

# 2. inspector.ts (16)
def fix_inspector(s: str) -> str:
    s = s.replace('type InspectorAreaViewGlobal = { InspectorAreaView: *FIX* };', 'type InspectorAreaViewGlobal = { InspectorAreaView: any };')
    s = s.replace('const inspectorAreaView = (): *FIX* =>', 'const inspectorAreaView = (): any =>')
    s = s.replace('const parsed: *FIX* = JSON.parse(cleaned);', 'const parsed: unknown = JSON.parse(cleaned);')
    s = s.replace('onSave: async (data: *FIX*) =>', 'onSave: async (data: Record<string, any>) =>')
    s = s.replace('Array.isArray((graphNode.properties as *FIX*)?.triggers)', 'Array.isArray((graphNode.properties as Record<string, any>)?.triggers)')
    s = s.replace('(graphNode.properties as *FIX*).triggers', '(graphNode.properties as Record<string, any>).triggers')
    s = s.replace('let triggerEdge: *FIX*;', 'let triggerEdge: any;')
    s = s.replace('.some((t: *FIX*) => t && t.id === triggerEdge.target)', '.some((t: any) => t && t.id === triggerEdge.target)')
    s = s.replace('const props: *FIX* = nodeProps', 'const props: Record<string, any> = nodeProps')
    s = s.replace('const triggerData: *FIX* = { ...props };', 'const triggerData: Record<string, any> = { ...props };')
    s = s.replace('.findIndex((t: *FIX*) => t && (t.id === targetId || t.id === triggerEdge?.target))',
                  '.findIndex((t: any) => t && (t.id === targetId || t.id === triggerEdge?.target))')
    return s
fix_file('static/js/inspector.ts', fix_inspector)

# 3. ui-controller.ts (16)
def fix_ui_controller(s: str) -> str:
    s = s.replace('// `*FIX*` because window.Lit.html', '// `any` because window.Lit.html')
    s = s.replace('...values: unknown[]): *FIX* => window.Lit.html', '...values: unknown[]): any => window.Lit.html')
    s = s.replace('renderAgentList(state: *FIX*) {', 'renderAgentList(state: any) {')
    s = s.replace('let orderInfo: Record<string, *FIX*> = {};', 'let orderInfo: Record<string, any> = {};')
    s = s.replace('🧍 for *FIX*thing', '🧍 for anything')
    s = s.replace('control-mode word *FIX*where else.', 'control-mode word anywhere else.')
    s = s.replace('@click=${(e: *FIX*) => { e.stopPropagation(); this.cancelSoak(name); }}', '@click=${(e: Event) => { e.stopPropagation(); this.cancelSoak(name); }}')
    s = s.replace('@click=${(e: *FIX*) => {\n                    e.stopPropagation();\n                    this.selectAgent(name);\n                }}',
                  '@click=${(e: Event) => {\n                    e.stopPropagation();\n                    this.selectAgent(name);\n                }}')
    s = s.replace('@click=${(e: *FIX*) => { e.stopPropagation(); if ((window as unknown as UIWin).graphManager)',
                  '@click=${(e: Event) => { e.stopPropagation(); if ((window as unknown as UIWin).graphManager)')
    s = s.replace('renderSelectedAgentOverview(state: *FIX*) {', 'renderSelectedAgentOverview(state: any) {')
    s = s.replace('renderAlerts(state: *FIX*) {', 'renderAlerts(state: any) {')
    s = s.replace('as [string, *FIX*][]) {', 'as [string, any][]) {')
    s = s.replace('renderTurnInfo(state: *FIX*) {', 'renderTurnInfo(state: any) {')
    s = s.replace('_renderInitiative(state: *FIX*) {', '_renderInitiative(state: any) {')
    s = s.replace('renderAll(state: *FIX*) {', 'renderAll(state: any) {')
    s = s.replace('// *FIX*thing, so on a large world', '// anything, so on a large world')
    return s
fix_file('static/js/ui-controller.ts', fix_ui_controller)

# 4. sky-scape.ts (13)
def fix_sky_scape(s: str) -> str:
    s = s.replace('span.*FIX*= html;', 'span.innerHTML = html;')
    s = s.replace('el.*FIX*= parts.join(\'\');', 'el.innerHTML = parts.join(\'\');')
    s = s.replace('grid.*FIX*= \'<div class="vwsky-empty">Could not load the outlook.</div>\';', 'grid.innerHTML = \'<div class="vwsky-empty">Could not load the outlook.</div>\';')
    s = s.replace('grid.*FIX*= _regionsTable(_regionsData);', 'grid.innerHTML = _regionsTable(_regionsData);')
    s = s.replace('canonical set plus *FIX* registry ids.', 'canonical set plus any registry ids.')
    s = s.replace('sel.*FIX*= \'<option value="">— weather</option>\' + ids.map((id) => {', 'sel.innerHTML = \'<option value="">- weather</option>\' + ids.map((id) => {')
    s = s.replace('sel.*FIX*= \'<option value="">- weather</option>\' + ids.map((id) => {', 'sel.innerHTML = \'<option value="">- weather</option>\' + ids.map((id) => {')
    s = s.replace('row.*FIX*= _entryFieldsHtml(e || { offset: _nextOffset() });', 'row.innerHTML = _entryFieldsHtml(e || { offset: _nextOffset() });')
    s = s.replace('box.*FIX*= \'\';', 'box.innerHTML = \'\';')
    s = s.replace('box.*FIX*= `<div class="vwsky-empty">No entries yet — add one, or pick a preset below.</div>`;',
                  'box.innerHTML = `<div class="vwsky-empty">No entries yet - add one, or pick a preset below.</div>`;')
    s = s.replace('box.*FIX*= `<div class="vwsky-empty">No entries yet - add one, or pick a preset below.</div>`;',
                  'box.innerHTML = `<div class="vwsky-empty">No entries yet - add one, or pick a preset below.</div>`;')
    s = s.replace('presets.*FIX*= SCHED_PRESETS.map((p, i) =>', 'presets.innerHTML = SCHED_PRESETS.map((p, i) =>')
    s = s.replace('tl.*FIX*= `<div class="vwsky-ruler">${ruler}</div>`', 'tl.innerHTML = `<div class="vwsky-ruler">${ruler}</div>`')
    s = s.replace('box.*FIX*=', 'box.innerHTML =')
    return s
fix_file('static/js/sky-scape.ts', fix_sky_scape)

# 5. event-stream.ts (12)
def fix_event_stream(s: str) -> str:
    s = s.replace('...values: unknown[]): *FIX* => window.Lit.html', '...values: unknown[]): any => window.Lit.html')
    s = s.replace('declare _areaEventLog: Record<string, *FIX*[]>;', 'declare _areaEventLog: Record<string, unknown[]>;')
    s = s.replace('Promise<*FIX*>', 'Promise<any>')
    s = s.replace('data: Record<string, *FIX*> = {}', 'data: Record<string, unknown> = {}')
    s = s.replace('meta: Record<string, *FIX*> = {}', 'meta: Record<string, unknown> = {}')
    s = s.replace('storeRawResponse(charName: string, phase: string, raw: string): *FIX* {', 'storeRawResponse(charName: string, phase: string, raw: string): any {')
    s = s.replace('getRawResponse(seq: number): *FIX* {', 'getRawResponse(seq: number): any {')
    s = s.replace('getAreaEvents(area: string): *FIX*[] {', 'getAreaEvents(area: string): unknown[] {')
    s = s.replace('(window as *FIX*).Dialog || (window as *FIX*).VW?.dialog', '(window as any).Dialog || (window as any).VW?.dialog')
    s = s.replace('`events: *FIX*`', '`events: any`')
    return s
fix_file('static/js/event-stream.ts', fix_event_stream)
