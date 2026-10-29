import subprocess
import re
import sys
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')

p = subprocess.run(['npx', 'tsc', '-p', 'tsconfig.check.json', '--noEmit'], capture_output=True, text=True, shell=True)
soak_errs = [l for l in p.stdout.splitlines() if 'static/js/soak/soak-ui.ts' in l]

print(f'Total errors in soak-ui.ts: {len(soak_errs)}')

# Group by error pattern
patterns = Counter()
for l in soak_errs:
    m = re.search(r'error TS\d+: (.*)', l)
    if m:
        # replace identifiers with <id>
        pat = re.sub(r"'[^']+'", '<id>', m.group(1))
        patterns[pat] += 1

for pat, c in patterns.most_common(15):
    print(f'{c:4d}  {pat}')
