---
type: task
status: todo
area: docs
priority: low
---

# task-658: js_module_index --check fails on room-context.js despite a complete @module/@contributes header

**Filed:** 2026-10-01
**Related:** 

## Goal

python tools/js_module_index.py --check exits 1 reporting 'New modules missing the @module/@contributes contract: static/js/agent/prompt-builder/room-context.js'. The header is complete (@module, @contributes, @powers, @relates) and the module IS listed in docs/design/js-module-index.md line 30, so the guard's parse is what is failing - most likely the '@contributes buildRoomContext/Parts' entry, whose slash-joined compound is not a plain comma-separated identifier list. Verified pre-existing on a clean master worktree (same message, exit 1), so not caused by task-313 which only edited the function bodies. Fix is to split the compound into two entries, then regenerate the index.

## Acceptance

- TODO
