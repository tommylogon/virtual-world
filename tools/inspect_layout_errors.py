import subprocess
import re
import sys
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')

p = subprocess.run(['npx', 'tsc', '-p', 'tsconfig.check.json', '--noEmit'], capture_output=True, text=True, shell=True)
errs = [l for l in p.stdout.splitlines() if 'static/js/graph/layout-engine.ts' in l]

print(f'Total errors in layout-engine.ts: {len(errs)}')

target_types = Counter()
for l in errs:
    m = re.search(r"Property '([^']+)' does not exist on type '([^']+)'", l)
    if m:
        target_types[m.group(2)] += 1

print('=== Failing types in layout-engine.ts ===')
for t, c in target_types.most_common(10):
    print(f'{c:4d}  {t}')

print('\n=== Sample errors ===')
for l in errs[:20]:
    print(l)
