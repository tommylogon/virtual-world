---
type: task
status: done
area: refactor
priority: medium
---

# task-462: Conditions single source of truth (data-driven JSON catalog)

**Filed:** 2026-09-22
**Related:** task-287, task-288, task-266

## Goal

Make data/library/conditions/*.json the single source of truth for condition definitions, mirroring the trait loader/seeder. Backfill the 15 hardcoded-only conditions, move CONDITION_HIERARCHY ordering and the perception-skip set into data fields (order/perception_skip/mature), add an in-place catalog reload for library edits, and fix the stale docs. No new engine features: the declarative schema already covers condition behavior; only id-keyed reactions (charmed/frightened/grappled/unconscious) stay in code.

## Acceptance

- [x] Every catalog condition has a `data/library/conditions/<id>.json` (38 files; the 15 hardcoded-only ones backfilled).
- [x] `CONDITION_HIERARCHY`, `PERCEPTION_SKIP`, `BLOCKING_CONDITIONS`, `PERIODIC_CONDITIONS`, `CONDITION_EXCLUSIONS`, `CONDITION_DEFAULT_TIMERS` and `MATURE_CONDITIONS` are derived from the catalog — no hand-maintained lists.
- [x] Ordering / perception-skip / mature gating are per-condition data fields (`order`, `perception_skip`, `mature`).
- [x] `seed_condition_library()` is idempotent and only *adds* missing keys to existing files (user edits preserved).
- [x] `reload_condition_library()` re-reads the library in place; the library API calls it after create/update/delete/rename, so edits apply without a restart.
- [x] Mature gating centralised: `Player.sync_pleasure_vitals` strips `MATURE_CONDITIONS`; library listings hide mature conditions when the toggle is off.
- [x] Docs updated (`Rules Engine/Conditions System.md`, `Library 2.0`).

## Implementation

- `engine/player_conditions.py` — bootstrap `order`/`perception_skip`/`mature` tables + `_normalize_catalog()`, `_BUILTIN_CONDITIONS`, `_rebuild_derived_constants()` (in place), `reload_condition_library()`, backfilling `seed_condition_library()`. `BLOCKING_CONDITIONS` is now a mutable `set` (frozensets can't be rebuilt in place); added `PERCEPTION_SKIP` / `MATURE_CONDITIONS`.
- `engine/conditions.py` — `perceived_conditions` uses the derived `PERCEPTION_SKIP`.
- `player.py` — `sync_pleasure_vitals` uses `MATURE_CONDITIONS`; re-exports the new names.
- `routes/library_ops.py` — `_filter_mature_entries` also filters conditions; `_reload_condition_catalog()` hooked into create/update/delete/rename.
- `data/library/conditions/*.json` — 15 new files; 23 existing gained only the 3 new keys.
- `tests/test_condition_catalog.py` — derived constants, seeder (coverage/idempotent/no-clobber) and reload.

## Verification

- `python -m pytest tests/test_condition_catalog.py tests/test_conditions.py tests/test_pleasure_system.py -q` → 104 passed.
- Full suite: 60 failed / 3313 passed — same 60 pre-existing failures as the documented baseline (`test_mcp_*`, `test_social_company`, `test_tick_time_scaling`) plus one unrelated scenario-naming failure from concurrent worktree changes. No condition-related regressions.
- `create_app({'TESTING': True})` smoke: 38 conditions, 22 in hierarchy, 10 mature.
- Derived values match the previous hardcoded constants exactly (dead→awake order, blocking set, etc.).

## Notes / follow-ups

- The 5 non-mature later additions (`social_breakdown`, `paranoid`, `hallucinating`, `itch`, `goosebumps`) are still outside the hierarchy, matching prior behavior; adding `order` to their JSON now moves them in.
- The library Conditions tab still uses a legacy `duration/severity/effects` editor (task-288) — the remaining gap to true tab-driven editing.
- Id-keyed engine reactions (`charmed`, `frightened`, `grappled`, `unconscious`/`dead`) intentionally stay in code.

## Review 2026-09-23 - closed

Verified: `tests/test_condition_catalog.py tests/test_conditions.py tests/test_pleasure_system.py` -> 104 passed; the 37 modified `data/library/conditions/*.json` in the working tree are just the library writer persisting the new empty `check_advantage`/`check_disadvantage` defaults. All acceptance boxes are checked. Open notes are owned elsewhere or by design: later-additions ordering, the legacy Conditions-tab editor (task-288), and id-keyed engine reactions staying in code. Closing.