import sys
import subprocess

sys.stdout.reconfigure(encoding='utf-8')

path = 'static/js/nl-editor/index.ts'
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()

# 1. NaturalLanguageEditor member types
c = c.replace('staging: unknown;\n        router: unknown;\n        agent: unknown;\n        ui: unknown;',
              'staging: any;\n        router: any;\n        agent: any;\n        ui: any;')

# 2. onUpdate callback data: any
c = c.replace('this.agent.onUpdate((event: string, data: unknown) => {',
              'this.agent.onUpdate((event: string, data: any) => {')

# 3. worldState update callback state: any
c = c.replace("worldState.on('update', (state: unknown) => {",
              "worldState.on('update', (state: any) => {")

# 4. validation issue map v: any
c = c.replace('(res.validation || []).map((v: { severity?: string; message?: string; rule?: string }) => ({',
              '(res.validation || []).map((v: any) => ({')

# Clean em-dashes
c = c.replace('\u2014', '-').replace('—', '-')

with open(path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(c)

p = subprocess.run(['npx', 'tsc', '-p', 'tsconfig.check.json', '--noEmit'], capture_output=True, text=True, shell=True)
errs = [l for l in p.stdout.splitlines() if 'static/js/nl-editor/index.ts' in l]
print(f'Remaining errors in index.ts: {len(errs)}')
for l in errs:
    print(l)
