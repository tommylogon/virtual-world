import sys
import subprocess

sys.stdout.reconfigure(encoding='utf-8')

path = 'static/js/item-library.ts'
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()

# 1. line 741 Object.entries
c = c.replace('for (const [id, node] of Object.entries(worldState.graph.nodes as Record<string, Record<string, unknown>>)) {',
              'for (const [id, rawNode] of Object.entries(worldState.graph.nodes as Record<string, Record<string, any>>)) {\n                const node = rawNode as any;')
c = c.replace('const name = node.name || id;',
              'const name = String(node.name || id);')

# 2. line 1012 triggers mapping
c = c.replace('window.Lit.render(itemLibraryHtmlTag`${(triggers as Array<Record<string, unknown>>).map((t: Record<string, unknown>, idx: number) => {',
              'const triggerList: any[] = Array.isArray(triggers) ? triggers : [];\n            window.Lit.render(itemLibraryHtmlTag`${triggerList.map((t: any, idx: number) => {')

# 3. line 1309 Object.entries and node/p typing
c = c.replace('for (const [nodeId, rawNode] of Object.entries(worldState.graph.nodes as Record<string, Record<string, unknown>>)) {',
              'for (const [nodeId, rawNode] of Object.entries(worldState.graph.nodes as Record<string, Record<string, any>>)) {')
c = c.replace('const node = rawNode;\n            if (node.type !== \'item\') continue;\n            const name = node.name || \'Unnamed\';\n            const id = name.toLowerCase().replace(/[^a-z0-9_]+/g, \'_\');\n            const p = node.properties || {};',
              'const node = rawNode as any;\n            if (node.type !== \'item\') continue;\n            const name = String(node.name || \'Unnamed\');\n            const id = name.toLowerCase().replace(/[^a-z0-9_]+/g, \'_\');\n            const p = (node.properties || {}) as any;')

# Clean em-dashes
c = c.replace('\u2014', '-').replace('—', '-')

with open(path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(c)

p = subprocess.run(['npx', 'tsc', '-p', 'tsconfig.check.json', '--noEmit'], capture_output=True, text=True, shell=True)
errs = [l for l in p.stdout.splitlines() if 'static/js/item-library.ts' in l]
print(f'Remaining errors in item-library.ts: {len(errs)}')
for l in errs:
    print(l)
