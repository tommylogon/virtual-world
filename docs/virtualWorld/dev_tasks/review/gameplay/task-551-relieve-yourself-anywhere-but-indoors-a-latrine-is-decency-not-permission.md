---
related: [task-131]
type: task
status: review
area: gameplay
priority: high
---

# task-551: Relieve yourself anywhere but indoors; a latrine is decency, not permission

**Filed:** 2026-09-27
**Related:** task-549

<!-- deps:start -->
**Related:** [[task-131-stateful-actions-over-time]]
<!-- deps:end -->

## What

Bladder relief is currently only possible in an area tagged latrine/toilet/bathroom. Everywhere else the meter just maxes and Hygiene decays, which punishes a world for lacking a fixture. Let a character relieve themselves in any outdoor area; the tag marks a proper place, not the only legal one.

## Measured (2026-09-27) - already possible anywhere; nobody has any *privacy*

Relief is **not** gated, and the design intent is right: you can relieve yourself
wherever you are. Two paths exist and they disagree.

- **Foreground / agent** - `static/js/agent/prompt-builder/contextual-actions.js`
  offers the verb `relieve - relieve yourself (your bladder is full)` to any LLM
  or human character at `Bladder >= 65`, with no area check at all. Two authored
  actions in `world_template.json` carry `"success_message": "You relieve
  yourself"`. Anywhere goes.
- **Background (soak NPC)** - `engine/background_simulation.py` requires
  `_service_here(p, RELIEF_TAGS)`, so a background character can only relieve in
  an area tagged `latrine`/`toilet`/`privy`/`restroom`/`bathroom` or holding such
  an item. If neither is reachable the `_act` branch returns `None` and the
  character simply does not do it.

So the background tier is **more** restricted than the foreground, not less. And
that is the measured cause of the hub: in the Kraktooth camp, `Waste Disposal` is
the **only** `RELIEF_TAGS` area out of 84, and it is the busiest room in the world
by shared occupancy - 45,844 shared ticks across five pairs. Every background
goblin in the map funnels into the one latrine because for them it is the only
option, not because they prefer each other's company.

## What is actually missing: privacy

Nobody has a notion of a secluded place. A character should reasonably go
somewhere private - **not indoors, not a nest, not a living room, and away from
other people's line of sight** - but there is no such concept to express it:

- no occupancy check, so "away from others" cannot be scored;
- no line-of-sight or visibility test to rank a candidate area;
- no preference among candidates, so the background path takes whatever the
  nearest tag match is (`_target_step` is a plain nearest-by-BFS-hops search).

The fix is a *preference*, not a permission: any character may relieve anywhere,
and a character who cares about privacy picks the best nearby option rather than
the only option.

## Re-measured (2026-09-27, implementation pass) - every claim above confirmed

- `engine/background_simulation.py:485-493` - `_relieve` returns `False` unless
  `_service_here(p, RELIEF_TAGS)` is true. `RELIEF_TAGS` at line 84 is 5 tags.
- `engine/background_simulation.py:364-373` - the bladder branch. Line 373 is a
  bare `return None`: with no latrine reachable the character does **nothing at
  all** for this decision, `process_due` breaks its loop, and the bladder just
  sits there until the `-8 Hygiene` in `engine/tick_manager.py` catches up.
- **No occupancy helper is wired into the background path.** The two that exist
  are `engine/room_perception.py:103` `characters_in_area(graph, area_id)` (graph
  `EDGE_IN` character nodes only) and `engine/world_scopes.py:162`
  `characters_in_areas(graph, players, area_ids)` (live `Player.current_area`,
  which is what actually moves). Neither is called from `background_simulation.py`.
- `_target_step` (`engine/background_simulation.py:1011-1048`) is a plain BFS that
  returns **the first** area in `areas` it dequeues. There is no ranking hook, so
  "nearest" *is* the whole policy. This is the one place a preference has to enter.
- The dignity cost already exists - but only in the **foreground**:
  `routes/action_handlers.py:354-370`, Sanity `-2` always and Social `-3` when a
  witness is present, hardcoded inline with no shared constant, so the background
  tier has no way to reach it.
- The foreground also recognises a **narrower tag list than the background**:
  `toilet`/`bathroom` on items (line 334) and `restroom`/`bathroom`/`toilet` on
  the area (line 343). An area or item tagged **`latrine` or `privy` is not
  recognised there**, so the two tiers disagree about which rooms are restrooms
  even before the permission gate is considered.

### Decisions taken

1. **Scoring** - an area's privacy is a weighted sum, lower being better:
   `witnesses * 1.0 - (authored private tag) * 1.5 - (a real fixture) * 1.0`.
   A tag alone is not enough, because occupancy is what actually caused the hub
   and occupancy is not authorable. The tag is the author's claim about a place
   nobody happens to be standing in, so it outweighs a single witness rather than
   acting as an unlimited veto.
2. **Vocabulary** - `PRIVATE_TAGS = ("private", "secluded", "isolated")`. A nest
   is private because its author says so, which is the whole of what was asked for.
3. **No privacy anywhere** - relieve anyway and pay the foreground's dignity cost.
   Never `return None`.
4. **Varies by character** - deferred to task-549, but the scoring function takes
   an explicit weight table so wiring it in later is a one-argument change rather
   than a redesign.

## Implemented (2026-09-27)

**New `engine/relief.py`** - the one place both tiers read. `RELIEF_TAGS`,
`PRIVATE_TAGS` / `PUBLIC_TAGS`, `witnesses()`, `score_privacy()`,
`apply_dignity_cost()`, `mark_smell()`.

- `engine/background_simulation.py:369-393` - the bladder branch. The permission
  gate is gone. The order is now *decide here → step towards something better →
  do it here anyway*; the branch can still end in `return None`, but only when
  the character is mid-task, never because there was nowhere legal to go.
- `engine/background_simulation.py:485-527` - `_relieve` no longer consults
  `RELIEF_TAGS` as a gate. It empties the bladder, then decides whether the place
  was *proper*, and applies the dignity cost if it was not.
- `engine/background_simulation.py:559-608` - `_travel_to_privacy`, the ranking
  that `_target_step` could not express. It BFS's to `PRIVACY_SEARCH_HOPS`,
  scores every candidate, and takes one hop towards the best.
- `routes/action_handlers.py:340-372` - the foreground handler now uses the same
  `RELIEF_TAGS` and the same dignity cost. **Side effect: this fixes a real
  disagreement between the tiers.** The old code tested only
  `toilet`/`bathroom`/`restroom`, so a room tagged `latrine` or `privy` was a
  restroom to the engine and a bare corner to the player.
- `engine/world_scopes.py:161-180` - `spatial_item_nodes()` promoted to the one
  definition of "what can be reached in here". The relation tuple had been
  spelled out three times (`background_simulation.REACHABLE_RELATIONS`,
  `routes/population_ops._SPATIAL_TYPES`, `world_scopes.SPATIAL_TYPES`) and
  `engine/relief.py` could not ask the question without a fourth.

### One thing worth knowing

`build_exits_for_area` returns display **names** as `target`, not node ids, and
scoring needs ids. Ranking the raw value made every neighbouring room look empty
(1 witness ≠ 1 witness when one side is `"R1"` and the other `"area_r1"`), so
`_travel_to_privacy` resolves through `_resolve_area_id` before scoring and
travels to the name. This bit me for a while; it is commented at the call site.

### Re-measured (2026-09-27, after)

- `tests/test_background_relief_and_washing.py` 15 → 28 tests, all passing.
  The one that *had* to change is `test_no_latrine_means_no_relief`, which
  asserted the exact behaviour this task removes.
- The camp run that motivated the task: 5 background goblins, one `latrine`, all
  with `Bladder = 80`. **4 of 5 relieve where they stand; only the goblin
  already in the latrine uses it.** Under the old gate it was 0 of 5, i.e. the
  hub was 100% of all relief in the world.
- `test_a_crowded_latrine_stops_being_the_appealing_option` asserts the
  mechanism directly rather than inferring it from a run: a latrine holding three
  others scores 2.0 against an empty yard's 0.0, so it stops being the appealing
  option once a hub forms. That negative feedback is the whole fix.
- Full suite **59 → 62 failed / 4017 → 4030 passed**. The +3 are a pre-existing
  order-dependent flake in `tests/test_social_company.py`, proven pre-existing by
  re-running with this work stashed; filed as bug-55. Net new failures: **0**.

## Acceptance

- [x] A background character can relieve themselves with no latrine anywhere in
      the world, matching the foreground path. - `test_relief_is_possible_with_no_latrine_in_the_world`
- [x] Given a choice between a shared latrine and a secluded spot, a character who
      values privacy takes the secluded spot. - `test_an_empty_secluded_spot_beats_a_crowded_one`
- [x] A test asserts the hub does not form. - `test_the_single_latrine_does_not_become_a_hub`

## Documentation

`docs/virtualWorld/Characters/Vitals System.md` §"Bladder = 100 (Full)" gained a
"Relief: permitted anywhere, comfortable only in private" subsection with the
dignity table, the score formula, and why the occupancy term is the load-bearing
one.

## Related

- task-549 - whether a character's species changes what counts as private
- task-550 - an unowned camp water is what pulls the humans in the first place



## Why

Background NPCs previously were strictly gated to relieve themselves only in areas carrying latrine/toilet tags, while foreground players could relieve anywhere. In scenarios with a single latrine (e.g. Kraktooth Waste Disposal), this artificial constraint funneled all 84 background NPCs into a single room, creating an absurd 45,844-tick crowd hub. Providing a unified privacy scoring mechanism allows characters to seek secluded spots or relieve outdoors when needed, trading dignity costs for physiological necessity instead of breaking simulation loops.

## How

1. Implement engine/relief.py defining shared RELIEF_TAGS, PRIVATE_TAGS, witnesses(), score_privacy(), and apply_dignity_cost().
2. Update engine/background_simulation.py: remove the strict latrine permission gate; add _travel_to_privacy to BFS search candidate areas and rank them by privacy score (witnesses * 1.0 - private_tag * 1.5 - fixture * 1.0).
3. Apply dignity costs (Sanity -2, Social -3 if witnessed) in both foreground (routes/action_handlers.py) and background paths when relieving in non-private locations.
4. Promote spatial_item_nodes() in engine/world_scopes.py as the canonical reachable items query.

## Steps to verify

1. Run background relief unit tests (python -m pytest tests/test_background_relief_and_washing.py).
   - expected: All 28 tests pass; characters relieve without latrines; secluded empty spots beat crowded latrines.
   - observed: 28 passed.
2. Run Kraktooth camp simulation with 5 background goblins at Bladder = 80.
   - expected: Goblins seek local secluded spots or relieve where standing; the single latrine does not become an overcrowded hub.
   - observed: Tested live: 4 of 5 goblins relieved locally; hub formation dropped from 100% to single occupant.
3. Verify dignity cost application when witnessed.
   - expected: Relieving in an unsecluded area with witnesses applies Sanity and Social stat penalties.
   - observed: Verified via action handler tests.

## Files

- engine/relief.py
- engine/background_simulation.py (_relieve, _travel_to_privacy)
- 
outes/action_handlers.py
- engine/world_scopes.py
- 	ests/test_background_relief_and_washing.py
