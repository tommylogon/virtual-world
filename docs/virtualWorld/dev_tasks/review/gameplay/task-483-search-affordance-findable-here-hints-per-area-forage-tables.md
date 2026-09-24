---
type: task
status: review
area: gameplay
priority: medium
---

# task-483: Search affordance, findable-here hints, per-area forage tables

**Filed:** 2026-09-23
**Related:** task-471; task-470; task-473

## Goal

Deferred from task-471: a 'find <skill>' help/UI affordance, HUD hints for what could be found in an area, and a per-area override + JSON library surface for the forage tables instead of the code constant.

## Acceptance

- [ ] The forage `SKILL_TABLES`, `SKILL_DISPLAY` and `AREA_SKILL_BONUS` live in
  **`data/library/foraging.json`** and are authoritative; the code keeps the old
  literals only as a fallback used when the file is missing or malformed.
- [ ] **Per-area override:** an area node's `forage_tables` property
  (`{skill: [entries]}`) adds local finds for that area and makes an otherwise
  unrecognised area searchable; an area without it behaves exactly as before.
- [ ] **Findable-here hints:** `findable_here()` / `findable_hint()` name the
  skills that could turn something up in an area (its tags plus any override),
  side-effect free so the UI can call them freely.
- [ ] The `find <skill>` affordance is discoverable — autocomplete suggests the
  search skills by name.
- [ ] Data-only: adding a table entry or an area override is JSON, no code change.
- [ ] Deterministic; no LLM.

## Progress — 2026-09-24

Backend and data implemented and tested; moving to review.

- **`data/library/foraging.json`** (new) — `skill_tables`, `skill_display` and
  `area_skill_bonus`, seeded exactly from the previous code constants, so
  behaviour is unchanged while becoming data.
- **`engine/foraging.py`** — loads the JSON as the authoritative tables (built-ins
  kept as `_DEFAULT_*` fallback so an unpackaged run still searches); new
  `AREA_TABLES_PROPERTY` + `_area_tables`, an `extra_entries` path through
  `_candidate_entries`, a per-area gate in `find_or_spawn`, and `findable_here()`
  / `findable_hint()`.
- **`engine/autocomplete.py`** — a `find`/`forage` branch suggests the search
  skills, so the `find <skill>` command is discoverable.
- **`tests/test_forage_tables.py`** (9) — the file is authoritative and covers all
  eight skills; missing file falls back; an override makes an untagged area
  searchable while a bare room stays barren; findable hints and their text.
  `test_autocomplete.py` gains a `find` case.

Remaining for this task: the actual **HUD display** of `findable_hint` in the
front-end (template/JS surface), which is a UI wiring follow-up; the query and
the data surface it needs are done.
