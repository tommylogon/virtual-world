---
type: task
status: todo
area: docs
priority: medium
---

# task-669: Backfill @docs headers on the 162 baselined Python modules

**Filed:** 2026-10-02
**Related:** task-576, task-578

## Goal

task-576 put the @module/@contributes/@docs contract and its guard over engine/ and routes/, and documented 18 core modules. The remaining 162 live in docs/design/py-module-baseline.txt. Each needs a real @module/@contributes/@docs header naming the note that documents it (or an explicit @docs none with a one-line reason for a thin registrar or pure utility). The guard already fails a NEW Python module without the header, so this is a ratchet-down of existing debt, not a new mechanism. Work in batches and remove each path from the baseline as it lands; use python tools/js_module_index.py --check to confirm.

## Acceptance

- TODO
