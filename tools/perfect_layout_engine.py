import sys
import subprocess

sys.stdout.reconfigure(encoding='utf-8')

path = 'static/js/graph/layout-engine.ts'
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()

# 1. LayoutNodeUpdate optional x, y
c = c.replace('type LayoutNodeUpdate = { id: string | number; x: number; y: number;',
              'type LayoutNodeUpdate = { id: string | number; x?: number; y?: number;')

# 2. adj typing
c = c.replace('const adj: Record<string, Record<string, unknown>> = {};',
              'const adj: Record<string, Record<string, any>> = {};')

# 3. gridPosition array/object support
c = c.replace('const p = cell || {};',
              'const p = (Array.isArray(cell) ? { x: cell[0], y: cell[1] } : (cell || {})) as { x?: number; y?: number };')

# 4. hasPaintedCoords cell typing
c = c.replace('const cell = (properties || {}).cell;',
              'const cell = ((properties || {}) as any).cell;')

# 5. nodeData in nodeWorldCoords
c = c.replace('nodeData: Record<string, unknown> | null | undefined',
              'nodeData: any')
c = c.replace('const props = (nodeData && nodeData.properties) || {};',
              'const props = (nodeData && (nodeData as any).properties) || {};')

# 6. frozen(u.id)
c = c.replace('!frozen(u.id)', '!frozen(String(u.id))')
c = c.replace('nodesObj[id]', 'nodesObj[String(id)]')

# 7. line 260 String(u.id)
c = c.replace('anchorFor(u.id)', 'anchorFor(String(u.id))')

# Clean em-dashes
c = c.replace('\u2014', '-').replace('—', '-')

with open(path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(c)

p = subprocess.run(['npx', 'tsc', '-p', 'tsconfig.check.json', '--noEmit'], capture_output=True, text=True, shell=True)
errs = [l for l in p.stdout.splitlines() if 'static/js/graph/layout-engine.ts' in l]
print(f'Remaining errors in layout-engine.ts: {len(errs)}')
for l in errs:
    print(l)
