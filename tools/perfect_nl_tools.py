import sys
import subprocess
import re

sys.stdout.reconfigure(encoding='utf-8')

path = 'static/js/nl-editor/tools.ts'
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()

# 1. updates casting in _resolveNode
c = c.replace('const updates = this.staging.getStagedUpdates();',
              'const updates = this.staging.getStagedUpdates() as Record<string, any>;')

# 2. _registryToEntries
c = c.replace('_registryToEntries(res: unknown): LibraryEntry[] {',
              '_registryToEntries(res: any): LibraryEntry[] {')
c = c.replace('Object.entries(res as Record<string, unknown>).map(([key, entry]: [string, unknown]) => ({',
              'Object.entries(res as Record<string, unknown>).map(([key, entry]: [string, any]) => ({')

# 3. execute signature
c = c.replace('async execute(toolName: string, args: Record<string, unknown> = {}, context: Record<string, unknown> = {}): Promise<unknown> {',
              'async execute(toolName: string, args: Record<string, any> = {}, context: Record<string, any> = {}): Promise<any> {')

# 4. Clean em-dashes
c = c.replace('\u2014', '-').replace('—', '-')

with open(path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(c)

p = subprocess.run(['npx', 'tsc', '-p', 'tsconfig.check.json', '--noEmit'], capture_output=True, text=True, shell=True)
errs = [l for l in p.stdout.splitlines() if 'static/js/nl-editor/tools.ts' in l]
print(f'Remaining errors in tools.ts: {len(errs)}')
for l in errs:
    print(l)
