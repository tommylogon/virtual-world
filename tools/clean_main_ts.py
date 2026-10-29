import sys
import subprocess

sys.stdout.reconfigure(encoding='utf-8')

path = 'static/js/main.ts'
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()

c = c.replace('function connectSummary(res: unknown, payload: unknown)', 'function connectSummary(res: any, payload: any)')
c = c.replace('[name, r]: [string, unknown]', '[name, r]: [string, any]')
c = c.replace('[n, r]: [string, unknown]', '[n, r]: [string, any]')
c = c.replace('const data = result.data;', 'const data = (result.data || {}) as Record<string, any>;')
c = c.replace("el.value = val ?? '';", "el.value = String(val ?? '');")
c = c.replace('catch (err: unknown) {', 'catch (err: any) {')
c = c.replace("worldState.on('update', (state: unknown) => {", "worldState.on('update', (state: any) => {")
c = c.replace('const narrationUi = (window as unknown as { narrationUI?: unknown }).narrationUI;', 'const narrationUi = (window as unknown as { narrationUI?: any }).narrationUI;')

# Also clean any em-dashes
c = c.replace('\u2014', '-').replace('—', '-')

with open(path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(c)

p = subprocess.run(['npx', 'tsc', '-p', 'tsconfig.check.json', '--noEmit'], capture_output=True, text=True, shell=True)
errs = [l for l in p.stdout.splitlines() if 'static/js/main.ts' in l]
print(f'Remaining errors in main.ts: {len(errs)}')
for l in errs:
    print(l)
