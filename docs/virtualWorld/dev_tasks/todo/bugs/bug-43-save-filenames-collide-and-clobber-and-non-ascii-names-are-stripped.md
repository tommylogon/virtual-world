---
type: bug
status: todo
area: bugs
priority: medium
---

# bug-43: Save filenames collide and clobber, and non-ASCII names are stripped

**Filed:** 2026-09-22
**Related:** bug-31

## Symptom

Two data-loss / nameless-file problems in save filename generation:

1. **Collision clobbers.** `_save_game` names a new save
   `<safe_name>_YYYYMMDD_HHMMSS.json` with a second-resolution timestamp and no
   uniqueness guard. Saving twice with the same name inside the same second writes the
   second state over the first file with no warning. The current `saves/` list already
   holds several distinct runs all named `test save`, so the pattern is real.
2. **Non-ASCII stripped.** The sanitizer
   `''.join(c if c.isalnum() or c in ' _-' else '_' for c in name)` replaces every
   character outside ASCII alphanumerics/space/underscore/hyphen with `_`. A name like
   `Ærø kysten` or `Draghál` loses its letters — ids/filenames become rows of
   underscores. `str.isalnum()` is Unicode-aware, so the filter is stricter than it
   needs to be for a filesystem name.

Note: `bug-31` covers path *validation* (traversal). This is filename *generation*.

## Root cause

- `routes/helpers.py:293` — sanitizer drops non-ASCII letters.
- `routes/helpers.py:310` — `filename = f"{safe_name}_{ts}.json"`, no collision check.
- Same sanitizer is duplicated in the rename route (`routes/saveload.py:312`), the
  scenario-name route (`saveload.py:793`), and the scenario path helper
  (`saveload.py:638`), so a fix must be applied consistently or the sites will drift.

## Fix

1. Resolve a free filename: if the target exists, append a numeric/disambiguating
   suffix (`..._2`, `..._3`) — never silently overwrite a different save. Slot
   overwrites (`slot=` / autosave) stay the one intentional in-place overwrite.
2. Normalize names (NFKD) and keep Unicode letters/digits, folding only characters
   that are genuinely unsafe on Windows (`<>:"/\|?*`, control chars). Fall back to a
   stable placeholder only if the result is empty.
3. Factor the sanitizer into one shared helper so `_save_game`, rename, and scenario
   naming use the same rules.

## Acceptance

- [ ] Saving two different states with the same name in the same second yields two
      files; neither overwrites the other.
- [ ] A save named with non-ASCII letters keeps those letters in the filename (or at
      least does not become all underscores), and the save still loads.
- [ ] Overwriting an existing slot via 💾 still replaces that same file in place.
- [ ] Path traversal remains rejected (`_safe_save_path`); add cases for the new
      unicode/normalization path.

## Files

- `routes/helpers.py` — `_save_game` sanitizer + filename (282-326)
- `routes/saveload.py` — rename sanitizer (312), scenario name (793), `_safe_scenario_name` (638)
- `tests/test_saveload.py` — collision and unicode coverage
