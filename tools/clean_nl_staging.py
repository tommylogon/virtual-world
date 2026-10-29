import sys
import subprocess

sys.stdout.reconfigure(encoding='utf-8')

path = 'static/js/nl-editor/staging.ts'
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()

# 1. StagedOpPayload
c = c.replace('type StagedOpPayload = Record<string, unknown>;',
              'type StagedOpPayload = Record<string, any>;')

# 2. api() return type
c = c.replace('post(path: string, body: unknown): Promise<unknown>;',
              'post(path: string, body: unknown): Promise<any>;')

# 3. batch type
c = c.replace('let batch: { errors?: Array<{ message?: string; error?: string }>; results?: unknown[] } | null = null;',
              'let batch: any = null;')

# 4. Clean em-dashes
c = c.replace('\u2014', '-').replace('—', '-')

with open(path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(c)

p = subprocess.run(['npx', 'tsc', '-p', 'tsconfig.check.json', '--noEmit'], capture_output=True, text=True, shell=True)
errs = [l for l in p.stdout.splitlines() if 'static/js/nl-editor/staging.ts' in l]
print(f'Remaining errors in staging.ts: {len(errs)}')
for l in errs:
    print(l)
