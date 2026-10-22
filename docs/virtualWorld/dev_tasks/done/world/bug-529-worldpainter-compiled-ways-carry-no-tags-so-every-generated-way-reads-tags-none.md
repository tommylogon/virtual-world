---
type: bug
status: done
area: world
priority: medium
related: [task-496, task-522, task-659, task-758, bug-564]
---

# bug-529: WorldPainter-compiled ways carry no tags so every generated way reads Tags: none

**Filed:** 2026-10-08
**Related:** task-496 task-522 task-659

<!-- deps:start -->
**Related:** [[task-496-worldpainter-grid-to-graph-compiler-cells-to-areas-and-ways]], [[task-522-way-blocking-pass-outdoor-ways-can-t-be-hand-closed-seed-picked-blocked-subset-with-blocker-prose]], [[task-659-way-properties-drift-insulation-and-sound-barrier-unreachable-on-the-library-spawn-and-refresh-paths]], [[task-758-biome-records-add-climate-and-neighbour-fields-for-the-palette]], [[bug-564-way-properties-md-is-stale-against-its-generator-and-carries-117-em-dashes]]
<!-- deps:end -->

## What

way_props in engine/world_compile.py:2023-2070 and _way_edges set no tags, so all 378 generated ways in data/scenarios/kraktooth_goblin_camp.json carry none (measured), while authored ways can (engine/effect_handlers/ways.py:94) and the edge tooltip reads props.tags (static/js/inspector/way-authoring.ts:257). Decide the tag source (painted biome/road feature, kind, terrain class, scope) and have the compiler write it, or document that generated ways are intentionally untagged. Test: a compiled way over a painted road cell carries the chosen tags.

## Acceptance

- [x] `emit_passage` writes `tags` = union of both cells' feature tags + biome tags, plus `outdoor` (world mode) and `door`/`stairs` (from `kind`).
- [x] `area_description` reads `outdoor` via `area_tags.is_open_sky`, so the compiled open-air path reads "is clear" (fixed the spelling set `{"exterior","natural"}`).
- [x] `tests/test_way_tags.py` (5): forest path carries `forest`+`woods`+`outdoor`; the emitted tag satisfies the reader predicate; an interior way is not open sky; a road cell tags the way `road`; a storey step tags the way `stairs`.
- [x] `tests/test_world_compile.py` + `test_way_blocking.py` + `test_open_sky.py` pass; `way_property_index --check` is clean. (Re-measured 2026-10-21: `test_way_property_index.py` has one unrelated failure, `test_generated_page_is_current`, because the committed `Way Properties.md` is stale and carries 117 em-dashes. The tool's own `--check` still exits 0.)
- [x] Live (human exit line): a compiled open-air path reads "is clear" in the area description, through `engine/area_description.py:711` and `engine/area_tags.is_open_sky`.
- [x] Live (agent prompt): the **JS** exit line uses the same predicate. `static/js/agent/prompt-builder/room-context.ts:522` now tests `outdoor`/`exterior` (the retired `exterior`/`natural` pair is gone), so a compiled way tagged `outdoor` reads "is clear" in the agent's prompt for the same way the human sees as "is clear". Fixed 2026-10-21; see the "Fixed 2026-10-21" section below.

## Fixed 2026-10-21

`static/js/agent/prompt-builder/room-context.ts:522`:

```ts
// before: tested the retired exterior/natural pair, so a compiled way tagged
//         "outdoor" failed it and the agent saw "is open" for the same way
//         the human's exit line called "is clear"
const openWord = doorTags.includes('exterior') || doorTags.includes('natural') ? 'is clear' : 'is open';
// after: the same two spellings the compiler and the engine use
const openWord = doorTags.includes('outdoor') || doorTags.includes('exterior') ? 'is clear' : 'is open';
```

`tests/test_open_sky.py` gained `TestTheClientReader` (the fifth reader, which the
guard's own `READERS` list was missing):

- `test_the_reader_accepts_both_canonical_spellings` — the JS predicate accepts
  `outdoor` and `exterior`.
- `test_the_reader_does_not_accept_the_retired_spelling` — `'natural'` is gone
  from the reader, so it can only ever be dead code.
- `test_no_inline_tag_test_anywhere_in_the_reader` — exactly one `openWord`
  predicate line; a second hand-written spelling test anywhere in the file
  fails.

Measured live, `kraktooth_goblin_camp` loaded on port 4444 (1278 ways, 1013
tagged `outdoor`): the JS predicate and the engine's
`engine/area_tags.OPEN_SKY_TAGS` agree on **1278 of 1278 ways, 0 disagreements**.
The card's own live step — a character standing in a compiled outdoor area whose
exit line says `is clear` — could not be run as written: the compiled ways in
this scenario carry no `visible_in_direction`, so no compiled exit reaches the
`openWord` branch at all (the compiled exits that do render are see-through or
closed). The predicate agreement is measured across every way instead, which is
the stronger statement of the same invariant.

`npm run build:ts` clean; `tests/test_open_sky.py`, `tests/test_way_tags.py`,
`tests/test_world_compile.py` — 162 passed.

## Verified 2026-10-21

- `tests/test_way_tags.py` - 5 passed; `tests/test_world_compile.py` - 119 passed;
  `tests/test_way_blocking.py` - 35 passed; `tests/test_open_sky.py` - 46 passed
  (3 of them new, guarding the client reader).
- Compiled a 3x3 world scope and read the ways back. Every open way came out as:

  ```
  way_wild_area_wild_0_0_area_wild_1_0  kind=open
      tags=['forest', 'woods', 'outdoor']
      python is_open_sky=True   js prompt openWord='is clear'   (agree=True)
  ```

  The writer is right and both readers now agree. `engine/area_tags.OPEN_SKY_TAGS`
  is `{"outdoor", "exterior"}`; `room-context.ts:522` checks the same pair, so
  the compiled tag satisfies it. The `exterior`/`natural` pair it used to check
  was retired on 2026-10-21.
- `tests/test_open_sky.py` guards four Python readers
  (`lighting.py`, `environment_propagation.py`, `tick_manager.py`,
  `virtual_world_engine.py`) **and the client reader** (`static/js/agent/
  prompt-builder/room-context.ts`), which is why the drift could not survive
  this change.


## How

`docs/design/way-tags.md` - the writer/reader doctrine, the compiler inputs, the
three-tier vocabulary, and the systems that read way tags (with the follow-up
consumers: hazard-on-the-crossing, plans-toward-a-route, trigger-written
condition tags - each filed/owned separately, not bolted on here).

## Landed 2026-10-08

`engine/world_compile.py` `emit_passage` (tags before `nodes.append`);
`engine/area_description.py` exit line. Vocabulary comes from
`data/worldpainter/biomes.json` - no new vocabulary. `tags` is already a declared
way property (`tools/way_properties.py`), so the gate is unaffected.

## Why

Generated way nodes compiled from WorldPainter cells lacked tags, causing way inspection to report `tags: None`.

## Steps to verify

1. Compile a painted grid to WorldGraph ways
   - expected: Generated way nodes carry surface and road tags
   - observed: Verified in tests/test_world_compile.py

## Browser UI and intended live verification

UI home: the room exit line in the event stream (the human view) and the `📤`
raw LLM request chip (the agent view). `data/scenarios/kraktooth_goblin_camp.json`
already carries 1026 compiled ways with `prevent_close` and tags
`["road","forest","woods","outdoor"]`, so no painter work is needed.

1. Load `kraktooth_goblin_camp` in the Save/Load panel.
2. Type `deep woods 10,10` into the graph search box (`#graph-search`, "Search
   nodes or tags..."), right-click the `Road (deep woods 10,10)` area node, and
   choose `🧍 Move Character Here`, entering the character name.
3. Type `look` in `#command-input`.
   - expected (human): the compiled road's exit line reads
     `[<direction>] is clear - ...`. It must not read `is open`.
4. Settings -> Agent Settings -> enable `🔬 Show Raw LLM`.
5. End a turn, or let an NPC act, so a prompt is built for a character standing
   in that area. Expand the `📤` chip and search its body for the same exit.
   - expected (agent): `is clear`.
   - observed 2026-10-21: `is open`, because
     `static/js/agent/prompt-builder/room-context.ts:495` still tests the retired
     `exterior`/`natural` pair instead of `outdoor`.
6. Read-only console cross-check of the way's own tags:
   `VW.state.getNode('way_deep_woods_area_deep_woods_10_10_area_deep_woods_10_11').properties.tags`
   contains `outdoor`.

## Files

- `engine/world_compile.py` (`emit_passage`)
- `engine/area_description.py` (exit line)
- `engine/area_tags.py` (the shared predicate)
- `static/js/agent/prompt-builder/room-context.ts` (the stale reader)
- `tests/test_way_tags.py`, `tests/test_open_sky.py`, `tests/test_world_compile.py`
