---
type: bug
status: done
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

- [x] Saving two different states with the same name in the same second yields two
      files; neither overwrites the other.
- [x] A save named with non-ASCII letters keeps those letters in the filename (or at
      least does not become all underscores), and the save still loads.
- [x] Overwriting an existing slot via 💾 still replaces that same file in place.
- [x] Path traversal remains rejected (`_safe_save_path`); add cases for the new
      unicode/normalization path.

## Resolution (2026-09-24)

One shared `sanitize_filename(name, *, allow='', fallback='unnamed')` in
`routes/helpers.py` replaces all six ad-hoc copies (`helpers._save_scenario`,
`helpers._save_game`, `saveload` rename, `_safe_scenario_name`, `scenario/name`,
`scenario/commit`). It now:

- NFKC-normalises and keeps Unicode letters/digits (not just ASCII), so
  `Draghál` / `Ærø kysten` survive instead of collapsing to underscores. The
  task text said NFKD, but NFKD + an alnum-only filter peels the combining mark
  and turns `á` into `a_`; NFKC composes it, which is what the second acceptance
  criterion actually wants. Documented in the helper docstring.
- Folds only characters unsafe on a filesystem, trims Windows-hostile trailing
  dots/spaces, and escapes reserved stems (`CON`, `com1`, ...).
- Keeps scenario names' extra `.()` allowance via `allow='.()'`.

`unique_filename(dir, filename)` resolves same-second collisions to
`..._2.json`, `..._3.json`. `_save_game` uses it for named saves; slot/autosave
writes bypass it (the one intentional in-place overwrite). Rename uses it too,
unless the new name resolves back to the current file.

Note: only the *filename* is disambiguated on collision — the stored
`_save_metadata.name` display label is untouched (convention: rename ids, not
display names). Tests in `tests/test_saveload.py` (`TestSanitizeFilename`,
`TestSaveFilenameCollisions`, `TestSafeSavePath`).

## Files

- `routes/helpers.py` — `_save_game` sanitizer + filename (282-326)
- `routes/saveload.py` — rename sanitizer (312), scenario name (793), `_safe_scenario_name` (638)
- `tests/test_saveload.py` — collision and unicode coverage
