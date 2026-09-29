---
type: task
status: todo
area: library
priority: medium
related: [task-569, task-570, task-573, task-568, task-497]
---

# task-588: Investigate — where WorldPainter vocabularies live, and whether they belong in `data/library/`

**Filed:** 2026-09-29
**Related:** task-569, task-570, task-573, task-568, task-497
**Answers for:** Roadmap-core-systems.md, which recommends task-569 (resource consumer) and task-570 (hostile consumer) as the cheapest large win in the repository
**Blocks:** task-589 (a WorldPainter tab in the library) — the tab's shape depends on where the data ends up

## Goal

The instinct is that WorldPainter data belongs in `data/library/`, split per entry like everything else in there. The scope is **three things that are not alike**, and the first job is to find that out rather than assume they travel together:

- `data/worldpainter/biomes.json` — a **taxonomy**: 105 biome records plus `features`, `resource_distribution`, `hostile_distribution`. Read by the compiler to classify a painted cell.
- `data/worldpainter/interiors.json` — a **plan collection**: `version`, `_about` (17 prose lines), `plans` (**30** drawn floor plans), `fallback`. Read by `engine/interior_gen.py:52` to fill a building's interior. This one already looks a great deal like a library.
- **town** — **not data at all.** It is one of three `MODES` in `engine/world_grid.py:81` (`("world", "town", "interior")`), and its content rides on `features` inside `biomes.json` (town / village / building). There is no town file to move, and a plan that says "move town into the library" is planning to move something that does not exist as a unit.

**Do not start by splitting anything.** Question 1 below can invalidate the whole premise for two of the three, and the two consumers this is meant to unblock (task-569, task-570) must keep working whichever way it lands.

## What is there today (verified 2026-09-29)

**Readers are few and singular.**

- `engine/biomes.py:37` is the only direct load path for `biomes.json` (`load(path)` with an override). Everything else goes through it: `biomes()`, `features()`, `biome()`, `area_tags()`, `forage_skill_bonus()`, `resource_distribution()`, `hostile_distribution()`, `validate()`.
- `engine/interior_gen.py:52` is the only direct load path for `interiors.json`.
- **The browser never reads either file.** The WorldPainter gets a *derived vocabulary* from `routes/world_grid_ops.py:292-300` (`{id, name, ...}` per biome) and consumes it as `state.vocab.biomes` (`static/js/worldpainter/editor.js:241,2722`, `grid-model.js:84,603,625`). A per-file layout does not mean 105 fetches — worth stating explicitly, because it is the usual objection.

**The distributions cover only the wild biomes.** `tests/test_biomes.py:100-101` asserts `set(resource_distribution()) == set(hostile_distribution()) == <the wild set>`. The other 89 are made/structure and exempt by design (`biomes.py:426-428`). A split yields **105 files of which 16 carry rules**.

**`features` is a different entity class** that references biomes by id (`biomes.py:403` walks `rec.get("biomes")`). It is not a biome's property, and it is the closest thing `town` has to data.

**The library is an entity registry with a materialize path — that is the crux.** `routes/library_ops.py:17` declares `REGISTRY_TYPES = ['items', 'characters', 'areas', 'ways', 'traits', 'conditions', 'behaviours', 'tags', 'triggers', 'structures']`, and every one of those is something you can *place into a world*: `materialize_library_item` (`:145`), `placeItemFromLibrary({type, id})` from the frontend. A biome has no such path — it is read by a compiler, never instantiated.

**The registry and the filesystem have already drifted, and in two ways at once.** The folders are `areas, characters, conditions, items, rooms, tags, traits, triggers, ways`. So `rooms` exists on disk but is not a `REGISTRY_TYPE`, and `behaviours` and `structures` are registered types with no folder. The hardcoded list is the weak point in this design, and it is weak today, before this task changes anything.

**The deeper cause is that the library has two storage shapes.** `handle_library_list` (`library_ops.py:210-216`) reads `data/library/<type>.json` — one registry file — while the other types are folders of one-file-per-entry (`_library_type_count:24-31` counts files in a subdir). Both shapes are live, and neither `data/library/behaviours.json` nor `data/library/structures.json` exists, so those two registered types serve **empty, silently**, with no error. `data/library/rooms/` holds 526 KB across three files (including a *third* `world_template.json`, 98 KB) and nothing can reach it: `handle_library_list('rooms')` returns 400 "Unknown registry type".

**The taxonomy is cached and the cache is never invalidated.** `engine/biomes.py:111-127` keeps a module-level `_cache` keyed by path, with `load(path, fresh=False)`. `clear_cache()` exists at `:125` and is called by **nobody** — not by a route, not by a test. `engine/interior_gen.py` and `roles.py` have the same shape. So a hand edit to the JSON is not visible until the process restarts.

## The questions, in order

1. **Is a WorldPainter entry a library entity?** A library file, in all ten current types, is something that gets materialized into a graph. A biome is a compile-time **vocabulary**; a floor plan is an authored thing you instantiate. If those are two different kinds of thing, then `data/library/` is right for `interiors.json`, wrong for `biomes.json`, and the real answer is that the library needs to know about two kinds of entry. Answer this by reading how the ten types are loaded, served and materialized — not by analogy.
2. **What is the file boundary for each?** For biomes: identity record in one file per biome, with `features` and the two distributions inlined, or kept global? `features` is its own entity class; the distributions are per-biome rules that exist for only 16 of 105. For interiors: one file per plan plus a `fallback`, or the collection stays whole?
3. **Where does the cross-entry validation go?** `biomes.py:409-451` checks what no single file can see: unknown biome id in a distribution, a wild biome with no rules, a made/structure biome with rules, unknown tags, `max_chance < base_chance`. Per-file these become index-level checks and need a named owner.
4. **What must the load contract guarantee?** Ideally `engine/biomes.py`'s eight public functions and `interior_gen.py`'s surface keep their signatures and semantics, so task-569 and task-570 are unaffected by the answer. If a split forces a caller change, that is a cost to weigh, not a detail.
5. **What actually breaks?** Verify, do not assume: `routes/world_grid_ops.py:292-300` (derived vocabulary — likely fine), `tools/build_code_graph.py:397` (its `JSON_IGNORE` covers `world_template.json` but **not** `biomes.json` — check what 105 files does to that graph), `tools/lint_library.py` (task-573 wants it to read the biome file; one file or 105 changes that check's shape), and the write paths — **does the WorldPainter ever write a biome tag or a floor plan?** If it does, a 105-file layout is a write-path and locking decision, not a read-path one. Also settle where `clear_cache()` gets called from: an authoring surface needs a reload story, and today nothing calls it.
6. **What does it cost, honestly?** For: per-entry diffs, no whole-taxonomy conflicts, each record reviewable alone. Against: a taxonomy-wide change (adding a tag to 30 biomes) becomes 30 edits, and merge pressure moves from one file to a hundred. Who authors this data and how often decides which side wins — and for `interiors.json` the answer may be "one author, rarely touched", which makes the per-file case much weaker than it looks for biomes.

## Acceptance

- A written recommendation **per data set** — `biomes.json`, `interiors.json`, and an explicit statement about `town` — with the reasoning and the evidence for each of the six questions.
- Question 1 is answered first and explicitly, because two of the three answers follow from it.
- If the answer is "split": the migration is staged so the loader surfaces are unchanged, and the cross-entry validation in question 3 has a named home before any file moves.
- If the answer is "keep": the reason is written where the next person will read it, so this is not re-litigated on a hunch.
- `tools/build_code_graph.py` and `tools/lint_library.py` are each confirmed unaffected or given a follow-up.
- A stated answer to whether the library needs **two kinds of entry** (materializable entity vs compiler vocabulary), since task-589 depends on it.

## Note

This is an **investigation**: a recommendation with evidence is the deliverable, not a moved file. Nothing in task-569 or task-570 should wait on it — both can proceed against today's blob and be unaffected if the answer is "keep".
