---
type: task
status: review
area: characters
priority: high
wiki: "[[Persona]]"
related: [task-843, task-733, task-830]
---

# task-874: Character size, species and the Persona block survive a scenario save, a library save and a library import

**Filed:** 2026-10-18
**Related:** task-843, task-733, task-830

<!-- deps:start -->
**Related:** [[task-843-character-file-import-llm-converts-any-card-or-prose-to-the-persona-schema]], [[task-733-character-sheet-a-full-page-worldgraph-style-person-form-that-compiles-into-viwo-primitives]], [[task-830-mind-panel-persona-tab-for-advanced-appearance-personality-schema-with-compile-button]]
<!-- deps:end -->

## What

A character's `size` (task-605), its `species` (task-549) and its Persona block (the node property `properties.appearance`, `engine/character_appearance.RECORD_KEY`) survive a scenario save/load, a save to the library, and a library import.

Three separate loss paths, measured:

1. **Scenario save/load drops `size`.** `_serialize_player` writes `"size"` (`engine/serialization.py:154`) and `to_scenario_dict` does not strip it, so the key is in the file - but `_deserialize_player` (`engine/serialization.py:373`) never read it. `p.size` stayed `None`, so a tier set from the graph editor was gone on the next load.
2. **Save to Library drops `size`, `species` and the Persona block.** `_buildCharacterCard` (`static/js/inspector/agent-view.ts:2178`) builds the card from a fixed key list; none of the three was in it.
3. **Library import drops `size`, `species` and the Persona block.** `handle_library_import_character` (`routes/library_ops.py:879`) set stats, vitals, skills, traits, tags, personality and prose, and copied `image` / `profile_image` / `expressions` onto the node - but never read `size` or `species`, and never wrote `appearance`.

Measured, not assumed: `"size"` appears in 68 files and `"species"` in 35 under `data/library/characters/`, so the library already carries both; `"appearance"` appears in none, so the Persona block had never round-tripped through the library. `species` is the same one-line defect as `size` in the same import function, so it is fixed here rather than left as a knowingly half-fixed round trip.

## Why

`size` is a first-class character property (task-605), not a `size_*` trait, and it has two live readers (way `max_size` gating and per-area occupancy, task-653). A property with readers that silently resets to `None` on load is worse than an unset one: the authored world and the loaded world disagree and nothing says so. `species` gates services (task-549) on the same terms. The Persona block is the structured source of truth for appearance (task-507/828), and `task-830`'s Compile renders prose *from* it - so a library round-trip that drops it silently reverts the character to whatever prose was last compiled, with the structured record gone.

## How

Four small, source-of-truth-preserving changes. No new store, no new shape.

1. `engine/serialization.py::_deserialize_player`: read `size` next to `species` (`:392`), normalising to a valid tier or `None`. `None` must survive as `None`, because that is what lets an un-authored character fall through to its `size_*` trait (`engine/size.py:20-37`). A value outside `SIZE_TIERS` (a hand-edited or legacy save) becomes `None`.
2. `static/js/inspector/agent-view.ts::_buildCharacterCard`: add `size: player.size ?? null`, `species: player.species || null` and `appearance: charProps.appearance || {}` (the same `charProps` it already reads `image` from).
3. `routes/library_ops.py::handle_library_import_character`: set `player.size` (validated against `SIZE_TIERS` like `routes/player_ops.py:620-632`) and `player.species`, and write `cdata.get('appearance')` onto the character node's `properties` alongside `image`/`profile_image`/`expressions`.

## Browser UI and intended live verification

Intended UI home: the graph editor character form's size selector (writes `player.size` via `PATCH /api/players/<name>`) and the Mind panel Persona tab (writes `properties.appearance`, task-830).

Current availability: implemented 2026-10-18. Regression tests in `tests/test_serialization.py` and `tests/test_library_character_import.py` exercise the real routes and the real serializer. Live front end: the running server (`localhost:4444`) serves this worktree, and `InspectorAgentView._buildCharacterCard('Arix')` returns `size`, `species` and a populated `appearance` (`{identity: {age, gender, occupation, pronouns, sexuality, species}}`) - `appearance` was absent from the card before the change (live-checked 2026-10-18). The Python half needs a process restart to be live in a running server; the tests cover it.

Live steps when available:

1. Open the graph editor for a character, set size to `huge`, open the Persona tab and fill at least one structured field.
   - expected: size and the block are visible in the inspector.
2. Save to Library, then delete the character and import it back from the library.
   - expected: `size` is `huge`, `species` is set and the Persona fields are still populated.
3. Save the scenario, reload it.
   - expected: `size` is `huge` (path 1).

## Steps to verify

1. `python -m pytest tests/test_serialization.py tests/test_library_character_import.py`
   - expected: the deserialize/import round-trip keeps `size`/`species`/`appearance`, and an absent size stays `None`.
   - observed: 26 passed (5 new: 3 scenario round-trip, 2 library import), 2026-10-18.
2. Live front end: `InspectorAgentView._buildCharacterCard(name)` in the running page.
   - expected: the card carries `size`, `species` and `appearance`.
   - observed: `Arix` -> `size: null` (un-authored, correct), `species` key present, `appearance` populated, 2026-10-18.
3. `python tools/ts_convert.py check` (the front end changed).
   - expected: build + typecheck + lint clean.
   - observed: typecheck ok, lint ok, header survival ok, window guards ok; the 4 `unit` failures and the `module:check` failure are byte-identical on a clean `HEAD` worktree (A/B, 736 passed / 4 failed both ways), so they are pre-existing debt, not this change.
4. Live click-through (Save to Library -> import; scenario save/load).
   - expected: both survive.
   - observed: pending live browser click-through; the API-level round trip is proven by step 1.

## Acceptance

- [x] `_deserialize_player` reads `size`; a valid tier round-trips, `None` stays `None`, an unknown value becomes `None`.
- [x] `_buildCharacterCard` includes `size`, `species` and `appearance`.
- [x] `handle_library_import_character` sets `player.size` / `player.species` and writes `appearance` onto the node.
- [x] Targeted tests prove the mechanism (which value was read, which node key was written).
- [ ] Live: a size + Persona field survive save-to-library, import, and scenario save/load by clicking in the browser.

## Files

- `engine/serialization.py`
- `static/js/inspector/agent-view.ts`
- `static/js/inspector/agent-view.js`
- `routes/library_ops.py`
- `tests/test_serialization.py`
- `tests/test_library_character_import.py`
