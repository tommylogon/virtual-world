import sys
import subprocess

sys.stdout.reconfigure(encoding='utf-8')

path = 'static/js/item-library.ts'
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()

# 1. triggers.map t: any
c = c.replace('triggers.map((t: Record<string, unknown>, idx: number) => {',
              'triggers.map((t: any, idx: number) => {')
c = c.replace('const effects: Array<Record<string, unknown>> = t.effects || [];',
              'const effects: any[] = t.effects || [];')

# 2. _buildEffectDetail
c = c.replace('_buildEffectDetail(effects: Array<Record<string, unknown>>)',
              '_buildEffectDetail(effects: any[])')
c = c.replace('const first = effects?.[0] || {};',
              'const first = (effects?.[0] || {}) as any;')
c = c.replace('const params = first.params || {};',
              'const params = (first.params || {}) as any;')

# 3. targetOpts string values
c = c.replace('const lbl = node.name || id;',
              'const lbl = String(node.name || id);')
c = c.replace('targetOpts.push({ value: exit.way_id, label: `🚪 ${exit.way_id}` });',
              'targetOpts.push({ value: String(exit.way_id), label: `🚪 ${exit.way_id}` });')
c = c.replace('const itemName = item.name || item.id || item;',
              'const itemName = String(item.name || item.id || item);')
c = c.replace('const lbl = it.name || id;',
              'const lbl = String(it.name || id);')

# 4. DocPreview format fallback
c = c.replace('const f: DocPreview = DocPanel ? DocPanel.format(rows)\n                    : { empty: !(rows && (rows as unknown[]).length), title: ((rows as Array<Record<string, unknown>>)?.[0]?.title) || \'\', url: null };',
              'const f: DocPreview = DocPanel ? DocPanel.format(rows)\n                    : { empty: !(rows && (rows as any[]).length), title: String(((rows as any[])?.[0]?.title) || \'\'), url: null };')

# Clean em-dashes
c = c.replace('\u2014', '-').replace('—', '-')

with open(path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(c)

p = subprocess.run(['npx', 'tsc', '-p', 'tsconfig.check.json', '--noEmit'], capture_output=True, text=True, shell=True)
errs = [l for l in p.stdout.splitlines() if 'static/js/item-library.ts' in l]
print(f'Remaining errors in item-library.ts: {len(errs)}')
for l in errs[:20]:
    print(l)
