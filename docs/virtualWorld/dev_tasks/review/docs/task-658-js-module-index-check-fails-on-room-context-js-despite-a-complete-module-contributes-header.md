---
type: task
status: review
area: docs
priority: low
---

# task-658: js_module_index --check fails on room-context.js despite a complete @module/@contributes header

**Filed:** 2026-10-01
**Related:** 

## Goal

python tools/js_module_index.py --check exits 1 reporting 'New modules missing the @module/@contributes contract: static/js/agent/prompt-builder/room-context.js'. The header is complete (@module, @contributes, @powers, @relates) and the module IS listed in docs/design/js-module-index.md line 30, so the guard's parse is what is failing - most likely the '@contributes buildRoomContext/Parts' entry, whose slash-joined compound is not a plain comma-separated identifier list. Verified pre-existing on a clean master worktree (same message, exit 1), so not caused by task-313 which only edited the function bodies. Fix is to split the compound into two entries, then regenerate the index.

## Root cause (measured 2026-10-02, not the guessed one)

The filed guess was the `@contributes buildRoomContext/Parts` compound. That is
not the failure. `static/js/agent/prompt-builder/room-context.js` begins with a
UTF-8 BOM (`ef bb bf`); `parse()` read with `encoding="utf-8"`, so the BOM stayed
as `\ufeff` before `/**`, `_leading_block`'s `startswith(("/*", "//", "/**"))`
failed on the first line, and the whole header parsed as `{}`. Every other JS
module has no BOM, which is why only this file was baselined.

## Resolution

- `tools/js_module_index.py` `parse()` now reads `utf-8-sig`, stripping a BOM.
  This is the robust fix: any future BOM'd module parses instead of silently
  dropping its header.
- Split the `@contributes` compound anyway, for legibility, into
  `buildRoomContext, buildRoomContextParts, ...`.
- Re-baselined (`0 uncovered`), regenerated `docs/design/js-module-index.md`
  (157 documented, 0 awaiting).

## Acceptance

- [x] `python tools/js_module_index.py --check` exits 0:
      `Contract check OK (0 known-uncovered, 0 known-bad-@docs, no new).`
- [x] Index regenerated; room-context.js appears under Documented modules.
- [x] The unaffected body text of the file was left alone; its 46 remaining
      mojibake markers are filed separately (task-668) as a content-encoding
      defect, not a contract defect.

## Follow-up

- task-668: `room-context.js` body is mojibaked (its UTF-8 bytes were decoded as
  cp1252 once, so em-dashes became a three-character sequence and emoji are
  damaged); not cleanly reversible.
