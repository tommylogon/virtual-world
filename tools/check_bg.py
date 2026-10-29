import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('static/js/graph/graph-background.ts', 'r', encoding='utf-8') as f:
    txt = f.read()

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

# check lines 2075-2085
for i, l in enumerate(txt.splitlines()):
    if 2070 <= i+1 <= 2090 or 2120 <= i+1 <= 2135:
        print(f'{i+1}: {repr(l)}')
