import sys
import subprocess
import re

sys.stdout.reconfigure(encoding='utf-8')

path = 'static/js/nl-editor/tools.ts'
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()

# 1. _mergeProps signature
c = c.replace('_mergeProps(base?: Record<string, unknown>, overlay?: Record<string, unknown>): Record<string, unknown>',
              '_mergeProps(base?: any, overlay?: any): Record<string, any>')

# 2. tags casts
c = c.replace('tags: node.properties?.tags || [],',
              'tags: (node.properties?.tags || []) as string[],')
c = c.replace('tags: view.properties?.tags || [],',
              'tags: (view.properties?.tags || []) as string[],')

# 3. _patchProps
c = c.replace('_patchProps(patch: Record<string, unknown> | null | undefined) {',
              '_patchProps(patch: any): Record<string, any> {')
c = c.replace('const props: Record<string, unknown> = { ...((patch || {}).properties || {}) };',
              'const props: Record<string, any> = { ...(((patch || {}).properties || {}) as Record<string, any>) };')

# 4. update_matching_nodes payload
c = c.replace('const payload = op.payload || {};',
              'const payload = (op.payload || {}) as Record<string, any>;')

# 5. autoDecorateProps tags
c = c.replace('const p: Record<string, unknown> = Object.assign({}, props);\n        p.tags = Array.isArray(p.tags) ? [...p.tags] : [];\n        const hasTag = (t: string) => (p.tags as string[]).includes(t);',
              'const p: Record<string, any> = Object.assign({}, props);\n        const tags: string[] = Array.isArray(p.tags) ? [...p.tags] : [];\n        p.tags = tags;\n        const hasTag = (t: string) => tags.includes(t);')

# 6. THEME_PACKS pack
c = re.sub(r'const pack = \(THEME_PACKS as [^)]+\)\[themeKey\] \|\| \(THEME_PACKS as [^)]+\)\[themeKey\.replace\(/s\$\/, \'\'\)\] \|\| null;',
           'const pack = (THEME_PACKS as any)[themeKey] || (THEME_PACKS as any)[themeKey.replace(/s$/, \'\')] || null;', c)
c = c.replace('pack.items.slice(0, count).map(([name, props]: [string, Record<string, unknown>]) =>',
              '(pack.items || []).slice(0, count).map(([name, props]: [string, any]) =>')

# Clean em-dashes
c = c.replace('\u2014', '-').replace('—', '-')

with open(path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(c)

p = subprocess.run(['npx', 'tsc', '-p', 'tsconfig.check.json', '--noEmit'], capture_output=True, text=True, shell=True)
errs = [l for l in p.stdout.splitlines() if 'static/js/nl-editor/tools.ts' in l]
print(f'Remaining errors in tools.ts: {len(errs)}')
for l in errs[:20]:
    print(l)
