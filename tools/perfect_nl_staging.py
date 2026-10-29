import sys
import subprocess

sys.stdout.reconfigure(encoding='utf-8')

path = 'static/js/nl-editor/staging.ts'
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()

# 1. api() return type
c = c.replace('return ApiClient as unknown as {\n            post(path: string, body: unknown): Promise<any>;\n            createNode(data: unknown): Promise<unknown>;\n            createEdge(from: string, to: string, type: string, props?: unknown): Promise<unknown>;\n            deleteEdge(from: string, to: string, type: string): Promise<unknown>;\n            deleteNode(nodeId: string): Promise<unknown>;\n            updateNode(nodeId: string, changes: unknown): Promise<unknown>;\n            placeItemFromLibrary(target: unknown, libraryId: string): Promise<unknown>;\n        };',
              'return ApiClient as any;')

# 2. errs mapping in batch.errors
c = c.replace('(batch.errors || []).map((er: { message?: string; error?: string }) =>',
              '(batch.errors || []).map((er: any) =>')

# Clean em-dashes
c = c.replace('\u2014', '-').replace('—', '-')

with open(path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(c)

p = subprocess.run(['npx', 'tsc', '-p', 'tsconfig.check.json', '--noEmit'], capture_output=True, text=True, shell=True)
errs = [l for l in p.stdout.splitlines() if 'static/js/nl-editor/staging.ts' in l]
print(f'Remaining errors in staging.ts: {len(errs)}')
for l in errs:
    print(l)
