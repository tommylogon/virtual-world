---
group: Library
---
# Library Lint Validator (tools/lint_library.py)

**Filed**: 2026-08-21  
**Priority**: High  
**Status**: In Progress â€” implementing `tools/lint_library.py` (2026-08-21)

---

## Summary

One reusable lint script that catches the data-quality problems we keep finding
by hand: dead interest tags, wearables missing `equip_slots`, tag case drift,
singleton tags, broken `contents` references, and sparse area tags. Script-first;
optional route integration later.

This is the regression guard for task-326 (interest pass) and task-324 (domain
tagging), and a quality gate for task-9 (population engine reads tags â€” garbage
tags in, garbage rooms out).

## Checks (all observed as real problems)

1. **Dead interest tags** â€” character `interest_tags` matching zero item tags.
   Found 61/125 dead (49%) in the 2026-08-21 survey; satsuki/uzume/nia/nina/pam
   were 5â€“6/6 dead.
2. **Wearable missing equip_slots** â€” items tagged `clothing`/`armor` without
   `equip_slots`. Was 50/60 before tools/fix_item_equipment.py; must stay 0.
3. **Tag case drift** â€” same tag in multiple casings across items/areas
   (`Container` vs `container`, `Consumable` vs `consumable` were live bugs).
4. **Singleton tags** â€” item tags appearing on exactly one item (`berry`,
   `necklace`, `guitar`) â€” each is either a typo or an under-connected concept;
   report, don't auto-fix.
5. **Broken contents refs** â€” library item `contents` pointing at missing
   library ids (currently only a runtime warning at spawn time,
   routes/library_routes.py:179).
6. **Area tag coverage** â€” library areas with no tags (35/58 as of survey);
   informational for task-324.

## Work Plan

1. `tools/lint_library.py`:
   - Loads `data/library/{items,characters,areas}/*.json`
   - Runs checks 1â€“6; exit code 1 on errors (checks 1â€“3, 5), warnings only for
     4 and 6
   - `--check <name>` to run a single check; default all
   - Output: per-file lines + summary counts (grep-friendly)
2. Optional follow-up (separate commit): expose as
   `GET /api/library/lint` so the editor's World Issues panel (#validation-section)
   can show library problems alongside trigger validation
   (engine/trigger_validator.py pattern).

## Files

- `tools/lint_library.py` (new script)
- optional: `routes/library_routes.py` (lint endpoint), `static/js/ui/*` (panel)

## Verification

- Run against current tree: expects **0 errors** after task-326 lands
  (before that, check 1 reports the known dead tags â€” useful as a worklist)
- Deliberately break a copy of one file â†’ lint catches it â†’ restore

## Dependencies

- None. Run it before AND after task-326/task-324 data passes.
- Feeds: task-9 (tag quality gate), future library edits (CI-able)
