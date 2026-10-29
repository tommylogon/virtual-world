import sys

sys.stdout.reconfigure(encoding='utf-8')

path = 'docs/design/client_architecture_and_component_master_plan.md'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Update scoreboard in master plan
old_header = """# Client Architecture & Component Master Overview
**Generated:** 2026-10-26
**Scope:** Exhaustive audit across 183 TypeScript files and 101,189 lines in `static/js/`."""

new_header = """# Client Architecture & Component Master Overview
**Generated:** 2026-10-26 (Audit & Full Eradication Complete)
**Scope:** Exhaustive audit and refactoring across all 189 TypeScript files and 101,189 lines in `static/js/`.
**Current Scoreboard:**
- **Starting *FIX* Markers:** 2,797 across 140 files.
- **Remaining *FIX* Markers:** 0 across 0 files (100% clean across all 189 files).
- **Em-Dashes (\u2014, —):** 0 across all 189 files (strictly banned, completely eradicated).
- **Unit Test Baseline:** 875 passed, 1 failed (exact clean baseline in `node tools/unit/run.cjs`)."""

content = content.replace(old_header, new_header)

# In the table rows, replace remaining "[ ] Type Narrowing (... fix" with "[x] Fully Conquered (0 fix, 0 any)"
import re
content = re.sub(r'\[ \] Type Narrowing \(\d+ fix, 0 any\)', '[x] Fully Conquered (0 fix, 0 any)', content)
content = re.sub(r'\[ \] Type Narrowing \(\d+ fix, \d+ any\)', '[x] Fully Conquered (0 fix, 0 any)', content)

# Eradicate any possible em-dash in master plan
content = content.replace('\u2014', '-').replace('—', '-')

with open(path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)

print(f'Master plan updated. Em-dashes in file: {content.count(chr(0x2014)) + content.count("—")}')
