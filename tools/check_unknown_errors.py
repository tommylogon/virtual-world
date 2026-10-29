import subprocess
import re
import sys
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')

p = subprocess.run(['npx', 'tsc', '-p', 'tsconfig.check.json', '--noEmit'], capture_output=True, text=True, shell=True)
unknown_files = Counter()

for l in p.stdout.splitlines():
    if "does not exist on type 'unknown'" in l:
        file = l.split('(')[0]
        unknown_files[file] += 1

print('=== Top Files with "does not exist on type \'unknown\'" ===')
for f, c in unknown_files.most_common(20):
    print(f'{c:4d}  {f}')
print('Total unknown errors:', sum(unknown_files.values()))
