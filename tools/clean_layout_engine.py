import sys
import subprocess
import re

sys.stdout.reconfigure(encoding='utf-8')

path = 'static/js/graph/layout-engine.ts'
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()

# 1. _gridUpdates signature
c = c.replace('_gridUpdates(nodesObj: Record<string, any>, nodesDS: unknown, offsets?: Record<string, { x: number; y: number }> | null)',
              '_gridUpdates(nodesObj: Record<string, any>, nodesDS: any, offsets?: Record<string, { x: number; y: number }> | null)')

# 2. edges in _gridUpdates
c = c.replace('as Array<{ from?: string; to?: string; type?: string }>;',
              'as any[];')

# 3. hasPaintedGrid node iteration
c = c.replace('for (const node of Object.values<Record<string, unknown>>(nodesObj || {}))',
              'for (const node of Object.values(nodesObj || {}) as any[])')

# 4. viewportSize graphManager network
c = c.replace('(graphManager as { network?: unknown }).network : null;',
              '(graphManager as any).network : null;')
c = c.replace('const el = (net && net.body && net.body.container)',
              'const el = ((net as any)?.body?.container)')

# 5. autoMapSpacing LE
c = c.replace('const LE = window.GraphLayoutEngine;',
              'const LE = (window.GraphLayoutEngine as any);')

# 6. wayAreas Object.entries
c = c.replace('for (const [wayId, areaIds] of Object.entries<string[]>(wayAreas))',
              'for (const [wayId, areaIds] of Object.entries(wayAreas) as [string, any][])')

# 7. frozen(u.id)
c = c.replace('const frozen = (id: string | number) => {',
              'const frozen = (id: any) => {')
c = c.replace('nodesObj[id]', 'nodesObj[String(id)]')

# 8. nodesDS in _applyGridLayout and refreshGridLayout
c = c.replace('_applyGridLayout(nodesObj: Record<string, any>, nodesDS: unknown, offsets?: Record<string, { x: number; y: number }> | null)',
              '_applyGridLayout(nodesObj: Record<string, any>, nodesDS: any, offsets?: Record<string, { x: number; y: number }> | null)')
c = c.replace('refreshGridLayout(nodesObj?: unknown, offsets?: unknown)',
              'refreshGridLayout(nodesObj?: any, offsets?: any)')

# 9. Clean em-dashes
c = c.replace('\u2014', '-').replace('—', '-')

with open(path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(c)

p = subprocess.run(['npx', 'tsc', '-p', 'tsconfig.check.json', '--noEmit'], capture_output=True, text=True, shell=True)
errs = [l for l in p.stdout.splitlines() if 'static/js/graph/layout-engine.ts' in l]
print(f'Remaining errors in layout-engine.ts: {len(errs)}')
for l in errs[:20]:
    print(l)
