---
type: task
status: todo
area: gameplay
priority: medium
related: [task-745, task-190, task-187, task-475]
wiki: "[[World Building/Movement]]"
---

# task-594: Swimming as a navigation type, with diving and a limited air vital

**Filed:** 2026-09-30
**Related:** task-745, task-190, task-187, task-475

<!-- deps:start -->
**Related:** [[task-745-worldpainter-hazards-a-current-strength-paint-layer-plus-a-hazards-json-category-table]], [[task-190-more-conditions]], [[task-187-character-size-passage-movement]], [[task-475-soak-action-to-skill-mappings-and-traversal-gates]]
<!-- deps:end -->

## What

Add swimming as a movement/navigation type alongside walking. Moving over water should be possible at the surface; deep water should require diving, which costs air. Dive duration is bounded by a new Air vital that depletes underwater and refills at the surface, and reaching zero has a defined consequence (drowning damage, forced surfacing, or death - the design decision is the point of the task). Check whether an existing vital or condition can carry this before adding anything new, and reuse the existing movement/action machinery rather than branching inside it.

## Acceptance

- [ ] **Swimming is a navigation type** alongside walking: a character can move
      over water at the surface. Today the way-`requires` vocabulary is
      `("", "crawl", "climb", "jump")` (`tools/way_properties.py:197`) and
      `engine/traversal.py:112` is `WAY_VERBS = ("crawl", "climb", "jump")`.
      `way_kind()` (`engine/traversal.py:154-157`) returns `"go"` for any
      `requires` value outside that tuple, so `requires: swim` would silently
      degrade into an ordinary walk rather than be refused.
- [ ] **Deep water requires a dive**, and the dive is an action of its own
      rather than a modifier on walking. No dive verb exists.
- [ ] **A bounded air budget** that depletes while submerged and refills at the
      surface. There is no `Air` vital: `engine/vitals.py:33-56`
      (`VITAL_POLARITY`) holds **16** entries and none is `Air`, and
      `rg -c '"Air"' data/ --glob '*.json'` returns **0** files.
- [ ] **A defined zero-air consequence**, chosen deliberately and applied once.
      The existing carrier is the `suffocating` condition
      (`data/library/conditions/suffocating.json`): "No air. Every tick with no
      breath is one closer to blackout.", `blocks_actions` and
      `blocks_movement` true, `periodic {"Energy": -3, "HP": -2}`, `ends_on
      ["breathe", "unblock"]`. The card's own instruction is to reuse it rather
      than add a parallel one.
- [ ] **The existing movement and action machinery is reused**, not branched
      around: the `swim` verb belongs in the scoped action registry
      (task-491), the crossing check belongs in `engine/traversal.py`, and the
      air drain belongs in the tick loop with the other vitals.
- [ ] **Authored content exercises it**: a water area a character can swim into,
      and a deep one it cannot cross without diving. task-745's river family
      gives the vocabulary (5 river biome files; 24 of 411 biome files carry a
      water terrain - 18 `water`, 5 `underwater`, 1 `surface_water`) but no
      depth axis: `surface` is the ground *material*
      (`engine/biomes.py:463-486`), and `shallow_water` / `deep_water` are
      values of that field, read by nothing as depth.

## Why

Water is the one piece of terrain the engine refuses to model honestly. Today a
river is a hazard tag that rolls Athletics and, on a failure, leaves you `wet`:
there is no way to be in the water at all. A character who falls into a river
is on a riverbank, not in a river, and "swimming" appears in the code only as a
label with no verb behind it.

The consequence design is the point of the card. Three candidate outcomes -
drowning damage, forced surfacing, death - have very different consequences for
a simulation that runs for a week at a time, and the choice belongs to a
person, not to whichever branch was written first.

## How

1. **Pick the consequence first, and reuse `suffocating`.** It already means
   "no air", it already blocks movement and actions, and it already drains HP
   per tick with an `ends_on ["breathe", "unblock"]` escape. Decide whether the
   zero-air outcome is "suffocating until you surface" (reuse it as is) or
   "forced surfacing" (a new `ends_on` trigger) or "death" (a fatal condition
   on top). Do not add a second drowning condition.
2. **Carry the air budget where the other vitals live.** `engine/vitals.py`
   declares the polarity registry, `vital_rates.py` (the top-level module
   `engine/tick_manager.py:14` imports) the decay, and the tick loop drains
   them. An `Air` vital is a `resource` that decays while
   submerged and refills at the surface, but check first whether the engine
   supports a vital that only exists on some characters, or whether the air
   budget belongs in the suffocating condition's own clock.
3. **Add `swim` and `dive` as verbs.** `swim` joins the way `requires`
   vocabulary (`tools/way_properties.py:197`) and `engine/traversal.py`'s
   `WAY_VERBS`; `dive` joins the scoped action registry (task-491). The
   `SOAK_ACTIONS` entry `"swim": "Athletics"` (`engine/traversal.py:55`) is
   already there but is unwired - `skill_for()` (`:72`) and `is_routine()` (`:77`)
   have no callers, and task-475's own changelog entry records "there is no
   `swim`/`force` verb yet". Either wire that mapping to a real verb or delete
   it; a mapping that looks like support and is not is worse than none.
4. **Give water a depth axis.** `surface` is the ground material and must not
   be overloaded. A `depth` field on the water biomes (or a `deep_water` tag
   the compiler stamps onto the area) is what makes "deep water needs a dive"
   expressible.
5. **Wire the hazard consequences while you are there.**
   `engine/hazards.py::dc_for` has no engine caller: only
   `tools/hazard_index.py` (the gate), `routes/library_ops.py` (the library
   browser) and `tests/test_hazards.py` read it. `engine/movement.py` has **0**
   matches for water, swim or drown. task-745's `rapids` hazard already
   declares `on_fail.conditions ["wet", "suffocating"]`, so the data for a
   drowning consequence exists and is waiting for a consumer.

## Steps to verify

1. Put a character in a water area and try to move through it.
   - expected: the move is a swim, not a walk, and it is resolved by the normal
     movement machinery.
   - observed: (2026-10-20) not possible. There is no `swim` verb in
     `engine/` or `routes/`; the only mechanic-shaped match is the unwired
     `SOAK_ACTIONS` entry at `engine/traversal.py:55`.
2. Try to cross a deep-water way.
   - expected: the crossing is refused until the character dives.
   - observed: (2026-10-20) not possible. `WAY_VERBS` is
     `("crawl", "climb", "jump")` (`engine/traversal.py:112`) and `way_kind`
     (`:154`) degrades an unknown `requires` to `"go"`.
3. Dive and watch the air budget.
   - expected: air decreases only while submerged and refills at the surface.
   - observed: (2026-10-20) there is no air vital. `VITAL_POLARITY`
     (`engine/vitals.py:33-56`) has 16 entries and no `Air`; 0 files under
     `data/` declare one.
4. Run the air budget to zero.
   - expected: the chosen consequence fires exactly once, with no unbounded
     dive and no silent underflow.
   - observed: (2026-10-20) not reachable. `suffocating` is the existing
     carrier (`data/library/conditions/suffocating.json`) but no code path
     applies it yet: the only author is `data/worldpainter/hazards.json`
     (`rapids.on_fail.conditions`), and `dc_for` has no engine caller.

## Files

- `engine/traversal.py` (`WAY_VERBS`, `SOAK_ACTIONS`, the crossing check)
- `engine/vitals.py` (the vital polarity registry) and `vital_rates.py` (the
  vital decay the tick loop calls)
- `engine/player_conditions.py` and `data/library/conditions/suffocating.json`
  (the zero-air carrier)
- `engine/hazards.py`, `data/worldpainter/hazards.json` (the hazard table and
  its unwired consumer)
- `data/library/biomes/` (the water family; needs a depth axis)
- `tools/way_properties.py` (the `requires` vocabulary)

## Browser UI and intended live verification

Intended UI home: game view at a shoreline → character movement/action controls → water traversal result, air vital, and event stream. The swim and dive actions use the existing navigation/action surface; the water cell/area remains part of the world graph.

Current availability: re-measured 2026-10-20, swimming, deep-water diving, an
air vital, and the zero-air consequence are still proposed. The card correctly
leaves the consequence as a design decision, and this section does not pick one
or claim a working water mechanic. What *has* arrived since the card was filed
is the vocabulary this work has to land on: task-745's river biome family and
the `data/worldpainter/hazards.json` table, whose `rapids` entry already
declares `suffocating` as a failure consequence.

Live steps when available:
1. In a scratch scenario with authored shallow and deep water, move a character from shore across shallow water and inspect the resulting location and event.
   - expected: surface swimming reaches the adjacent water location using the normal movement resolution.
2. From deep water, attempt to move without diving, then begin a dive and inspect the air vital after each tick.
   - expected: deep-water movement is gated by the dive rule; air decreases only while submerged and refills at the surface.
3. Continue until the chosen zero-air consequence fires, then inspect the event stream, vital panel, and final position/state.
   - expected: the selected design outcome is explicit and occurs once; no unbounded dive or silent air underflow occurs.
4. Surface before air is exhausted and repeat the dive.
   - expected: air replenishes at the surface and the next dive starts from the documented amount.

This section is not a claim that planned UI exists or works today.

## Reconnaissance (2026-10-20) - still valid

Re-checked on 2026-10-20 against the code. Nothing newer implemented swimming,
diving or an air vital. The card's claim stands.

Measured:

- **No swim verb.** `rg -n "swim" engine/ routes/ --glob '*.py'` returns 11
  matches across 5 files. Nine are prose ("your head swims", "Black spots
  swim", "swimlane" in the soak telemetry); one is the docstring at
  `engine/traversal.py:10`; **one** is mechanic-shaped:
  `engine/traversal.py:55` `"swim": "Athletics"` inside `SOAK_ACTIONS`.
  That entry is unwired - `skill_for()` (`engine/traversal.py:72`) and
  `is_routine()` (`:77`) have **zero** callers outside their own module, and
  task-475's changelog entry says so outright: "there is no `swim`/`force` verb
  yet" (`docs/CHANGELOG.md:1436`).
- **No dive, no buoyancy.** `rg -i "\bdive\b|diving|buoyan" engine/ data/
  static/` returns **1** match in the whole tree, in a 2026-09-07 export log
  (prose).
- **No air vital.** `engine/vitals.py:33-56` (`VITAL_POLARITY`) declares
  **16** vitals - HP, Energy, Social, Hygiene, Sanity, Entertainment, Comfort,
  Mana, Satisfaction, Hunger, Thirst, Bladder, Arousal, Stimulation, Pleasure,
  Temperature - and `Air` is not among them. `rg -c '"Air"' data/ --glob
  '*.json'` returns **0** files.
- **No water gate.** The way `requires` vocabulary is `("", "crawl", "climb",
  "jump")` (`tools/way_properties.py:197`), `engine/traversal.py:112` is
  `WAY_VERBS = ("crawl", "climb", "jump")`, and `way_kind()` (`:154-157`)
  returns `"go"` for any `requires` outside that tuple. `engine/movement.py`
  has **0** matches for water, swim or drown.
- **Conditions: 41** files in `data/library/conditions/`, none of them an air
  or drowning condition. But `suffocating` is the right shape and is worth
  reusing rather than duplicating: "No air. Every tick with no breath is one
  closer to blackout", `blocks_actions` and `blocks_movement` true, `periodic
  {"Energy": -3, "HP": -2}`, `ends_on ["breathe", "unblock"]`
  (`data/library/conditions/suffocating.json`; mirrored in the engine catalog
  at `engine/player_conditions.py:221`). The engine reads it in three places
  (`engine/movement.py:397`, `engine/interrupts.py:40`, `engine/undead.py:51`),
  but **no code path applies it**: the only author is the hazards table.

What *did* land since the card was filed, and what it changes:

- **task-745** (commit `314eeff1`, 2026-10-17; card in review) added the river
  biome family and the hazards table: `data/library/biomes/river.json`,
  `river_calm.json`, `river_swift.json`, `river_rapids.json`,
  `underground_river.json` (5 files; 24 of 411 biome files carry a water
  terrain - 18 `water`, 5 `underwater`, 1 `surface_water`), and
  `data/worldpainter/hazards.json` with 7 hazards
  (river, rapids, cliff, fall, thorns, pit, bridge_jump). The `rapids` entry
  declares `on_fail.conditions ["wet", "suffocating"]` and `damage "2d6"`, so
  the data for a drowning consequence now exists.
- **But the hazard table has no engine consumer.** `engine/hazards.py::dc_for`
  is called only by `tools/hazard_index.py` (the gate) and
  `tests/test_hazards.py`; `engine/biomes.py:622` uses the registry for
  validation and `engine/world_grid.py:1568` reads the biome's `hazard_id`
  during grid compile. task-745's own acceptance says "[x] Compiler emission
  pass mapped to consumer task-747 (blocked by task-746)", so the crossing
  consequences are not applied yet.
- **There is still no depth axis.** `surface` is the ground *material*, and
  `engine/biomes.py:463-486` (`ground_surface`) is explicit that it is "not
  called `floor`" and is a different fact from the storey index. The river
  biomes carry `"surface": "shallow_water"` and `deep_water.json`,
  `ocean.json` and `waterfall.json` carry `"surface": "deep_water"`, but
  nothing reads those values as depth, and no water biome carries a
  "swimmable" tag.

Evidence counts: 1 unwired `swim` mapping, 0 dive or buoyancy matches, 16
declared vitals with no `Air`, 0 files declaring an `Air` vital, 41 condition
files, 7 hazards in the registry with no engine consumer, 5 river biome
files, 24 water biomes.

Verdict: STILL_VALID. The card is accurate as written and is kept in todo.
Its facts that drifted are the ones recorded above: the river biome family and
the hazards table now exist and change where this work lands, `suffocating` is
the existing zero-air carrier the card asks about, and the `SOAK_ACTIONS`
`"swim"` entry must not be mistaken for a verb. The card's `Related:` field,
which was empty, now names task-745, task-190, task-187 and task-475.

Two broken wikilinks in this card are recorded rather than hidden:

- The card's `wiki:` frontmatter points at `[[Gameplay/Action Resolution
  System]]`, and **no such note exists** in the vault. That was already true
  before this edit. `docs/virtualWorld/Features/traversal-abilities.md` and
  `docs/virtualWorld/World Building/Movement.md` are the notes that actually
  cover this subject; repointing the `wiki:` key would add this card to their
  `## Connected` blocks, which `tools/doc_connected.py --apply` owns, so it is
  left for a doc change with that tool in the loop.
- The `[[task-745-...]]` link is ambiguous only because task-745 currently
  exists twice, in `dev_tasks/inprogress/world/` and `dev_tasks/review/world/`
  (a duplicate-id error that `python tools/tasks.py validate` reports, along
  with the same fault on task-769, task-776, task-852 and task-855). Delete the
  stale copy and the link resolves.

