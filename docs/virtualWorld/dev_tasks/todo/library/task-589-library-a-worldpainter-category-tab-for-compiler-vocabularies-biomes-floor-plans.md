---
type: task
status: todo
area: library
priority: medium
blocked_by: [task-588]
related: [task-588, task-495, task-568]

# task-589: Library: a WorldPainter category/tab for compiler vocabularies (biomes, floor plans)

**Filed:** 2026-09-29
**Related:** task-588, task-495, task-568
**Blocked by:** task-588 (the tab's shape depends on where the data ends up)

## Goal

Surface biomes and interior floor plans in the library so an author can read and search them, without pretending they are materializable entities. Every current REGISTRY_TYPE can be placed into a world (`materialize_library_item`, `placeItemFromLibrary`); a biome is read by a compiler and an interior plan is instantiated by `interior_gen`, so they need a second kind of library entry: **browsable vocabulary, no place action**.

## It is an authoring surface, not a browser (verified 2026-09-29)

The question behind this task is sharper than "a tab": **right now there is no way to add a biome, a settlement feature or an interior plan without hand-editing JSON.** No route writes `biomes.json` or `interiors.json` — `engine/biomes.py:37` and `engine/interior_gen.py:52` are read-only paths, and the WorldPainter authors *grids*, not *vocabulary*.

And the engine already promised this would be data-only. `biomes.py:47-94` documents that cell kind, merge behaviour and not-a-place are tag/field driven precisely so that "a modder can add a `hedge` or a `turnstile` the same way" and "a modder adding a `cellar` or a `subway` gets the behaviour without a code change". The promise is kept at the engine layer and broken at every layer above it:

- **No UI.** The editor consumes `state.vocab.biomes` and cannot extend it.
- **No validation on save.** `biomes.validate()` (`biomes.py:409-451`) catches unknown biome ids, a wild biome with no rules, unknown tags, `max_chance < base_chance` — and is run by tests and lint only, never at the point of edit.
- **No reload.** `biomes.py:111-127` caches the taxonomy in a module-level `_cache`. `clear_cache()` exists at `:125` and is called by **nobody**. A hand edit is invisible until the server restarts.

So a read-only tab answers a question nobody is asking. This has to be **create / edit / delete with validation on save and a cache-invalidation story**, and that is a write path into compiler input — which is exactly why it is blocked by task-588 rather than started from here.

## The registry drift, precisely (verified 2026-09-29)

The library has **two storage shapes**, and that is the real defect rather than a missing folder:

- `handle_library_list` (`library_ops.py:210-216`) reads `data/library/<type>.json` — one registry file. `routes/structures_ops.py` does the same for structures (`STRUCTURES_REGISTRY = "structures.json"`, with list / preview / **save**).
- The other types are folders of one-file-per-entry; `_library_type_count:24-31` counts files in a subdir.

Neither `data/library/behaviours.json` nor `data/library/structures.json` **exists**, so two registered types serve empty, silently, with no error. `data/library/rooms/` holds 526 KB across three files — including a *third* `world_template.json` at 98 KB — and is unreachable: `rooms` is not in `REGISTRY_TYPES`, so the API returns 400 "Unknown registry type".

**The registry drift is already adjudicated — but re-verify the doc, it is six weeks old.** `docs/virtualWorld/Library System/Library 2.0 - Unified Library Design.md` checked this on 2026-08-17 and **task-291** (in review) carries the execution in Phase 3. Its findings, as of that date:

- **`rooms` — legacy alias of `areas`, "Delete."** The data agrees: `data/library/rooms/world_template.json` is 64 nodes / 2 players and still carries the dropped `item_registry` + `narration_mode` keys, against the root file's 239 nodes / 3. Its only remaining referrer is `tools/migrate_legacy_triggers.py:224`. **This is not this task's decision and not this task's job.**
- **`behaviours` — "Remove the tab/type" is the recommendation, and it looks wrong.** Re-checked 2026-09-29: the tab is fully built (`templates/index.html:568`, pane at `:697-714` with search, `newEntry('behaviours')`, `saveEntry('behaviours')`) and writes to `data/library/behaviours/<id>.json`, while `engine/npc_behaviors.py:486` reads only `player.behaviors[]`. So the shipped UI has a live authoring path that produces files the engine ignores — the same trap the doc records for traits, where the chosen fix was **unify**, not remove. Removal would delete a working editor rather than fix the missing engine side. Tracked as its own task; do not act on the doc's row.
- **`triggers` — keep.** Seven files, used as a blueprint store by the trigger graph editor. No tab, and that is fine.
- **`structures` — the doc is silent**, and it is the one type with a complete engine and **no UI at all**: `engine/structures.py:6` defines it as a "portable, internally-wired subgraph — areas + ways + items + residents", with `collect_structure` / `materialize_structure` / `summarize_structure`; `routes/structures.py` registers five routes including save and materialize; and nothing in `static/` or `templates/` mentions a structure template. It is reachable by curl only. Tracked as its own task.

**Correction to an earlier draft of this task: there is only one storage shape, not two.** `load_registry(data_dir, 'items.json')` maps the *filename* to a *directory* — `routes/helpers.py:201-206` strips `.json`, joins `data/library/<name>`, and `os.makedirs(..., exist_ok=True)`. Every registry is therefore already a folder of one file per entry, and `STRUCTURES_REGISTRY = "structures.json"` means `data/library/structures/`. No `behaviours.json` or `structures.json` file is ever read, and none is missing. (Side note worth filing separately: that `makedirs` runs on **read**, so a `GET /api/library/behaviours` creates an empty directory in the working tree.)

## What exists to reuse

**Why it is not just "add a type to the registry":** `routes/library_ops.py:17` declares `REGISTRY_TYPES = ['items', 'characters', 'areas', 'ways', 'traits', 'conditions', 'behaviours', 'tags', 'triggers', 'structures']`, and each of those resolves to something placeable. Adding `biomes` to that list would hand the UI a "place this biome in the world" action with no meaning behind it, and `handle_library_list` would serve them as if they were graph entities.

## What exists to reuse

**The WorldPainter already has a derived-vocabulary route.** `routes/world_grid_ops.py:292-300` serves `{id, name, ...}` per biome, and the editor consumes it as `state.vocab.biomes` (`static/js/worldpainter/editor.js:241,2722`, `grid-model.js:84,603,625`). The tab should read the **same** derivation rather than have the browser fetch JSON — otherwise this task creates the second source of truth the repo's invariants forbid. `engine/interior_gen.py:52` is the equivalent seam for the 30 floor plans in `interiors.json`.

**`routes/structures_ops.py` is the existing model for a registry with a save handler** — list / preview / save against one `structures.json`. If the vocabulary needs a write path, that is the shape to copy, not a new pattern.

## Open questions to answer in the design

1. **What is the smallest authoring loop that is honest?** Create a biome, see it in the editor's vocabulary, compile a scope that uses it, and get a validation error before the save if the record is malformed. Anything less leaves the author editing JSON.
2. **One tab or two?** `biomes` is a taxonomy of 105; `interiors` is 30 drawn plans. Plans are visual — they may deserve thumbnails and a different presentation than a tag list.
3. **Should `REGISTRY_TYPES` be derived from disk instead of declared, and should the two storage shapes be unified?** Fixing the drift (`rooms`, `behaviours`, `structures`) and the folder-vs-single-file split may be in scope, or may be its own task. Decide, do not leave it implicit.
4. **Where does the tab live** — alongside the existing library types, or as a separate panel? The library's own type list is a frontend concern (`static/js/**`), so this is a UI call.
5. **Who calls `clear_cache()`?** A save that lands on disk and leaves the running compiler on the old taxonomy is worse than no save at all.

## Acceptance

- A WorldPainter category/tab **creates, edits and deletes** biomes and interior plans, sourced from the same `engine/biomes.py` / `interior_gen.py` derivation the WorldPainter uses — **no** new read path and no second copy of the vocabulary.
- A save runs `biomes.validate()` first and refuses a record that would break a compiler invariant (unknown tags, a wild biome with no rules, `max_chance < base_chance`).
- A successful save invalidates the taxonomy cache, so the next compile uses it. A test proves it: save, then read back through `biomes.biomes()` without a restart.
- No "place in world" affordance appears for a vocabulary entry; if it does, task-588's answer said the entry is materializable and the tab is wrong.
- The `rooms` / `behaviours` / `structures` drift is fixed or explicitly filed as its own task, with the choice recorded here. `rooms` is **not** deleted on the strength of being unregistered.
