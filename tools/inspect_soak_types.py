import subprocess
import re
import sys
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')

p = subprocess.run(['npx', 'tsc', '-p', 'tsconfig.check.json', '--noEmit'], capture_output=True, text=True, shell=True)
soak_errs = [l for l in p.stdout.splitlines() if 'static/js/soak/soak-ui.ts' in l]

target_types = Counter()
for l in soak_errs:
    m = re.search(r"Property '([^']+)' does not exist on type '([^']+)'", l)
    if m:
        target_types[m.group(2)] += 1

for t, c in target_types.most_common(15):
    print(f'{c:4d}  {t}')
