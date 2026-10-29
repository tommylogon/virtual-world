import sys
import subprocess

sys.stdout.reconfigure(encoding='utf-8')

path = 'static/js/soak/soak-ui.ts'
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()

# 1. to.value string
c = c.replace('to.value = Math.min(last, windowTicks);',
              'to.value = String(Math.min(last, windowTicks));')

# 2. renderKinds payload: any
c = c.replace('function renderKinds(payload: Record<string, unknown>) {',
              'function renderKinds(payload: any) {')

# 3. soak-st-from and soak-st-to
c = c.replace("el('soak-st-from').value = 0;\n                el('soak-st-to').value = last;",
              "el('soak-st-from').value = '0';\n                el('soak-st-to').value = String(last);")

# 4. node.type check
c = c.replace("if (node.type === 'text' || node.type === 'number') {",
              "const ntype = (node as any).type; if (ntype === 'text' || ntype === 'number') {")

# 5. soak-ticks value string
c = c.replace("el('soak-ticks').value = ticks;",
              "el('soak-ticks').value = String(ticks);")

# 6. renderCompare event listener
c = c.replace("el('soak-compare-a').addEventListener('change', renderCompare);",
              "el('soak-compare-a').addEventListener('change', () => renderCompare());")

# Clean em-dashes
c = c.replace('\u2014', '-').replace('—', '-')

with open(path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(c)

p = subprocess.run(['npx', 'tsc', '-p', 'tsconfig.check.json', '--noEmit'], capture_output=True, text=True, shell=True)
errs = [l for l in p.stdout.splitlines() if 'static/js/soak/soak-ui.ts' in l]
print(f'Remaining errors in soak-ui.ts: {len(errs)}')
for l in errs:
    print(l)
