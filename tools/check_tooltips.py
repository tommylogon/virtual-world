import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('static/js/graph/tooltips.ts', 'r', encoding='utf-8') as f:
    txt = f.read()

txt = txt.replace('\u2014', ' - ').replace('—', ' - ')
txt = txt.replace('buildTooltip(nodeData: *FIX*) {', 'buildTooltip(nodeData: Record<string, unknown>) {')
txt = txt.replace('filter(([, playerData]: *FIX*) => playerData.current_area === nodeData.id)', 'filter(([, playerData]: [string, { current_area?: string }]) => playerData.current_area === nodeData.id)')
txt = txt.replace('filter(([, pd]: *FIX*) => pd.current_area === nodeData.id)', 'filter(([, pd]: [string, { current_area?: string }]) => pd.current_area === nodeData.id)')
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

for i, l in enumerate(txt.splitlines()):
    if '*FIX*' in l or '\u2014' in l or '—' in l:
        print(f'{i+1}: {repr(l)}')
