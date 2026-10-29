import subprocess
import re
import sys
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')

p = subprocess.run(['npx', 'tsc', '-p', 'tsconfig.check.json', '--noEmit'], capture_output=True, text=True, shell=True)
types_y = Counter()
properties = Counter()

for l in p.stdout.splitlines():
    m = re.search(r"Property '([^']+)' does not exist on type '([^']+)'", l)
    if m:
        properties[m.group(1)] += 1
        types_y[m.group(2)] += 1

print('=== Top 20 Failing Types (Y) ===')
for t, count in types_y.most_common(20):
    print(f'{count:4d}  {t}')

print('\n=== Top 20 Failing Properties (X) ===')
for prop, count in properties.most_common(20):
    print(f'{count:4d}  {prop}')
