import sys
import subprocess

sys.stdout.reconfigure(encoding='utf-8')

path = 'static/js/nl-editor/tools.ts'
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()

c = c.replace('catch (e: unknown)', 'catch (e: any)')
c = c.replace('catch (err: unknown)', 'catch (err: any)')
c = c.replace("const res = await apiGet('/api/tags/search?q=' + encodeURIComponent(args.query || ''));",
              "const res = (await apiGet('/api/tags/search?q=' + encodeURIComponent(args.query || '')) || []) as any[];")
c = c.replace("const res = await apiGet('/api/triggers/validate' + (qs ? ('?' + qs) : ''));",
              "const res = (await apiGet('/api/triggers/validate' + (qs ? ('?' + qs) : '')) || {}) as any;")

with open(path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(c)

p = subprocess.run(['npx', 'tsc', '-p', 'tsconfig.check.json', '--noEmit'], capture_output=True, text=True, shell=True)
errs = [l for l in p.stdout.splitlines() if 'static/js/nl-editor/tools.ts' in l]
print(f'Remaining errors in tools.ts: {len(errs)}')
for l in errs:
    print(l)
