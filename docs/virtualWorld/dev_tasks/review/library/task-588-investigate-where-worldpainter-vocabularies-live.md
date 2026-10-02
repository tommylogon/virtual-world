---
type: task
status: review
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

---

# Recommendation (2026-10-02, re-verified against the tree)

**Verdict: keep `biomes.json` and `interiors.json` where they are and whole. Do
not move either into `data/library/`, and do not split either into per-entry
files now. But the library does need a second kind of entry, and task-589 should
add it as a *read/edit vocabulary surface over the existing files*.**

## Q1 first — is a WorldPainter entry a library entity? **No, and the library needs two kinds of entry.**

Verified from the loading/materialize path, not by analogy. All ten
`REGISTRY_TYPES` resolve to something you can *place into a graph*:
`materialize_library_item` (`routes/library_ops.py:146`) and the frontend's
`placeItemFromLibrary`. A biome has **no materialize path** — the compiler reads
it to classify a painted cell and never instantiates it as a node. A floor plan
is closer: `interior_gen.template_for` instantiates it, but through a
*generation recipe* (`RECIPE_ID = "interior.v1"`), not the place action, and it
is a picture rather than a graph entity.

So the honest model is two kinds of library entry:

| kind | examples | verbs |
|---|---|---|
| **materializable entity** | items, characters, areas, ways, traits, conditions, behaviours, tags, triggers, structures | browse, edit, **place** |
| **compiler vocabulary** | biomes (+ features/distributions), interior floor plans | browse, edit, **no place action** |

This is why adding `biomes` to `REGISTRY_TYPES` is wrong (task-589 already says
so): it would hand the UI a "place this biome" action with no meaning and serve a
taxonomy as if it were graph entities. Task-589 should add the second kind
explicitly (a tab with create/edit/delete, validation-on-save, no place affordance).

## Per data set

### `data/worldpainter/biomes.json` — **keep whole, in place**

Re-verified: 105 biomes, 9 features, 16 resource-distribution + 16
hostile-distribution entries; 55,264 bytes. Reasons against splitting:

1. **Only 16 of 105 carry rules.** A split yields 105 files of which 89 are
   identity records. The distributions are per-biome rules for the wild set only
   (`biomes.py:426-428` exempts made/structure biomes).
2. **`features` is a different entity class** that references biomes by id
   (`biomes.py:403`). Splitting it forces a decision about an 11th file shape.
3. **The cross-entry validation is taxonomy-wide.** `biomes.validate()`
   (`biomes.py:409-451`) checks unknown ids, a wild biome with no rules, unknown
   tags, `max_chance < base_chance` — exactly the checks no single file can
   perform. Per-file makes them index-level checks with a new owner; that is a
   cost with no compensating benefit today.
4. **Merge cost.** Adding one tag to 30 biomes is 1 edit today and 30 after a
   split. The data is authored by one person and rarely touched (89 records have
   never carried rules).
5. **It is compiler input, not an entity registry.** It lives beside the library
   for the same reason `interiors.json` does: the compiler's vocabulary, not the
   graph's contents.

Per-entry diffs and conflict-free merges are real wins for *frequently,
independently* authored data. This data is neither.

### `data/worldpainter/interiors.json` — **keep whole for now**, revisit only if a write path exists

Re-verified: `version`, a 17-line `_about`, **30 plans**, one `fallback`; 11,597
bytes. It looks the most library-like (each plan is standalone and visual), and
*if* task-589 builds create/edit/delete, one-file-per-plan with `fallback` as a
reserved entry is the natural shape. But it is 30 plans, one author, rarely
touched, and a split now would be a migration with no consumer. **Recommendation:
ship task-589 against the single file first; split only when write volume makes
one-file-per-person a bottleneck,** and if so, name the index-level validator
(Q3) before moving anything.

### `town` — **not data at all; nothing to move**

Re-verified: `town` is one of three `MODES` in `engine/world_grid.py`
(`("world", "town", "interior")`). Its content rides on `features` inside
`biomes.json` (`town` / `village` / `building`). There is no `town.json` and no
town unit to relocate. Any plan that says "move town into the library" is
planning to move something that does not exist.

## Answers to the six questions

1. **Two kinds of entry — yes** (above). `data/library/` is the right home for
   neither vocabulary file today; the library *concept* needs the second kind,
   reachable through the **same derivation the WorldPainter already uses**.
2. **File boundary — one taxonomy-wide file for biomes; one collection for
   interiors** (with per-plan split deferred to the first real write path).
3. **Cross-entry validation — `engine/biomes.validate()` stays the one owner**,
   called by whatever save route task-589 adds, *before* writing. Do not create a
   second validator.
4. **Load contract — unchanged.** `biomes.py`'s eight public functions
   (`biomes`, `features`, `biome`, `area_tags`, `forage_skill_bonus`,
   `resource_distribution`, `hostile_distribution`, `validate`) and
   `interior_gen.py`'s surface keep their signatures, so task-569/task-570 are
   unaffected. Because we are not splitting, there is no caller cost at all.
5. **What breaks — verified:**
   - `routes/world_grid_ops.py:287` (`handle_painter_vocabulary`) derives
     `{id, name, tags, refusal}` from `biomes_mod.biomes()`; a save must go
     through `clear_cache()` for the editor to see it.
   - `tools/build_code_graph.py:397` `JSON_IGNORE` does **not** cover either
     file, but because they stay single files they contribute at most two graph
     nodes, not 105+30. No fix needed; a per-file split *would*.
   - `tools/lint_library.py` now reads `biomes.json` as one file (task-573,
     `biome_coverage`); a split would change that check's shape.
   - **Write paths: there are none.** No route or engine function writes
     `biomes.json` or `interiors.json` (grep of `open(...,"w")` / writers finds
     nothing). So this is a read-path decision, not a locking one — and a
     create/edit surface is genuinely new work for task-589.
   - `engine/biomes.py::clear_cache()` (`:125`) has **zero callers** (same for
     `roles.py:51`, `skill_progress.py:50`). Any authoring save must call it or
     the running compiler keeps the old taxonomy until restart.
6. **Cost — split loses today.** For: per-entry diffs, independent review.
   Against: a taxonomy-wide change becomes 30–105 edits, merge pressure moves
   from one file to a hundred, and validation fragments. One author, rarely
   touched → the per-file case for biomes is weak; for interiors it is a
   reasonable *later* change once edits are frequent.

## Consequences for task-589 (the dependent)

Task-589 is unblocked with this shape: add a **compiler-vocabulary** library
surface for biomes (and, secondarily, floor plans) that (a) reads through
`engine/biomes.biomes()` so there is no new read path or second vocabulary,
(b) runs `biomes.validate()` on save and refuses an invalid record, (c) calls
`clear_cache()` after a successful save, and (d) offers **no** "place in world"
action. The files stay where they are; task-589 becomes an editable view over
them rather than a migration.

`rooms` / `behaviours` / `structures` drift is out of scope here and already
owned elsewhere (task-645 / task-590 / task-591).
