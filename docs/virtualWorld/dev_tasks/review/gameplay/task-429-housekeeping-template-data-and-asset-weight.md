---
type: task
status: review
area: gameplay
priority: low
---

# task-429: Housekeeping — template data, asset weight, and the open data decisions

**Filed:** 2026-09-21  
**Relates:** task-408 (goblin scenario dedup/integrity), `world_template.json`.

Small, independent, and each one was noticed and deliberately deferred rather
than overlooked. Bundled so they are not lost.

## 1. `world_template.json` carries junk items

The boot template ships generated items with ids *and names* mangled together —
`item_bread_b4080839` named `Bread_b4080839`, `current_state: None`. They leaked
from a library-placement pass (`item_{name}_{timestamp}_{random}`). Any item in
the world can be found by a `FOOD_TAGS` search, so these make foraging tests and
searches ambiguous (they were what exposed the "identity, not id" note in
`tests/test_forage_reachability.py`).

Fix: audit the template for `_<8 hex/timestamp>` suffixed ids, either clean them
to authored ids or confirm they are intended, and check `current_state` is set.
Also worth a guard so a placement pass can never write generated ids into a
template again.

## 2. Template `mature_content`

`world_template.json` ships `mature_content: false` (the camp was flipped to true
on request). `player.py` documents that the arousal vitals only exist while the
toggle is on "so the base game never shows them", which reads as deliberate — but
the decision was never recorded. Decide: is mature off the intended default for a
new world, or should the template match the camp?

## 3. Savegames still carry the duplicate bulk

Scenario files dropped ~28% (`areas`/`rooms`/`ways`/`item_registry`) because they
are graph-only now. `_save_game` still uses `to_dict()`, so saves keep the full
projection. Deliberate so far — a savegame may be meant to be a complete snapshot
— but unrecorded. Decide and, if wanted, it's a one-line switch.

## 4. The 4.1 MB background PNG

`static/images/backgrounds/ChatGPT_Image_….png` is committed because the camp
scenario references it. At 3613×2408 it should be ~300–500 KB as JPEG or WebP.
Git history does not shrink without a rewrite, so the cheap moment is **now**,
while it is one commit deep rather than twenty.

## Acceptance

- No generated-id items in `world_template.json`; ids are authored and stable.
- A recorded decision on template `mature_content` and on savegame payload size.
- The background image re-encoded, or an explicit decision to keep it as is.

## Non-goals

- The goblin scenario's own data integrity (task-408).
- Any change to how scenarios or saves are *structured* — this is cleanup and
  decisions, not a format change.

## Resolution — 2026-10-02

### 1. `world_template.json` generated items — fixed

The task's example (`item_bread_b4080839` named `Bread_b4080839`) is already
gone: `bread` is `item_bread | bread | normal`, and **no node name is mangled**.
The 99 timestamp-looking nodes break down as 98 `logic_trigger` nodes (their
ids always embed a timestamp by design — `trigger_item_X_on_Y_<ts>_<rand>`) plus
exactly **one item**: `item_bush of berries_1788218658044_568` (a forage bush,
authored name, `current_state: normal`).

Renamed that item to the stable id `item_frost_crusted_berry_bush` across the
template (7 occurrences: node key, edges, trigger-id substring). Post-change
check: 239 nodes, 296 edges, **0 dangling edge endpoints**, and **0 remaining
generated-id items**; old id appears nowhere.

Guard (placement passes writing generated ids into a template): still open —
noted, not implemented, because it lives in the library-placement pass and is
its own change.

### 2. Template `mature_content` — decided: keep `false`

`data/scenarios/world_template.json` ships `mature_content: false`, and that is
the intended base-world default. `player.py` documents that the arousal vitals
only exist while the toggle is on "so the base game never shows them". The camp's
`true` is the deliberate exception, not the new default. No change.

### 3. Savegame payload — decided: keep the full `to_dict()` snapshot

`_save_game` (`routes/helpers.py:358`) and `save_autosave` (`:72`) use
`world.to_dict()`; scenario commit uses `world.to_scenario_dict()` (`:320`). The
split is intentional and worth keeping: a savegame must be a **self-contained**
snapshot independent of any scenario file, so it cannot drop the projection the
way scenarios did. Dropping it would make a save depend on an external file that
may be edited or absent. Recorded; no change.

### 4. Background assets — one orphan deleted, re-encode deferred

Measured: `static/images/backgrounds/` holds **18 files / 56.1 MB**. The task's
flagged file, `ChatGPT_Image_Sep_20_2026_02_50_11_PM-1789922605242-1790076612209.png`
(4,008 KB), has **0 references** anywhere in the repo (searched the whole tree
for `1789922605242`, and for the filename) — the camp now points at
`kraktooth-goblin-camp.png`. Deleted as a confirmed orphan.

The broader re-encode is deferred: nearly every remaining file is ≥4 MB, several
are referenced by `kraktooth_goblin_camp.json` (9 refs), `world_template.json`
(2), and `autosave.json` (2), and many filenames contain spaces (so automatic
orphan detection is unreliable). Converting to WebP and rewriting references
across scenarios/saves is its own task, not a housekeeping one-liner.
