# Roadmap

*Merged 2026-10-09 from `Roadmap.md` and `Roadmap-core-systems.md`. Part 1 is
the authored proposal (last revised 2026-09-30); Part 2 is the code audit
(2026-09-27). Headline counts are re-measured as of 2026-10-09; the dated
per-area audit figures in Part 2 are kept as written.*

*The live card list is generated, not hand-kept:*
`python tools/tasks.py roadmap --out docs/design/roadmap-computed.md`. Ordering
edges live in each card's `blocked_by`/`depends_on` frontmatter; `python tools/tasks.py graph` reports cycles and the critical path and
`python tools/tasks.py next` ranks what can start now.

## Part 1 - The three rules and the authoring priorities

Where the world is going, in what order, and why. This is a proposal, not a
promise: it is re-aimed whenever the simulation teaches us something.

*Written 2026-09-24, after `e4af71c`. Updated 2026-09-27 after `b885878`; again
2026-09-30 after `0369ef4`, which closed the floor-plan language gap this file
spent two revisions calling the last thing between a plan and a place. Last
updated 2026-09-30 after `33c253e` - three cards closed on live-browser
evidence, and the stale-card list below shortened by one.

### Where we are

| Status | Count |
|---|---|
| Done | 405 |
| Cancelled | 30 |
| Review | 272 |
| In progress | 18 |
| Todo | 92 |

(Counted from the folders, which are authoritative - not the frontmatter.
Re-measured 2026-10-09.)

**A floor plan is now a language, and a painted town is somewhere you live.**
The revision two days ago ended on the gap that blocked everything else: a
building you could enter was a building with nothing to paint inside it, because
`classroom`, `hallway` and `stairway` were unknown ids and a real plan compiled
to bare places plus a warning. That is closed. `data/worldpainter/biomes.json`
carries **53 indoor rooms** across thirteen purposes, plus a `stairway` that is a
*passable* cell and agrees with the stairwell the compiler already minted
(task-568). Merging became per-kind, so a corridor is one corridor whatever the
scope's switch says and a terrace of cottages is three cottages (task-564). A step
past three storeys is refused in words - *"The climb is 6 storeys of bare ground -
you would need a path cut into it"* - and a road painted across it opens the step
(task-525). **A building brings its own interior**: 30 drawn plans covering all 31
building types, painted as cells so the standard compiler builds the rooms and an
author edits them by editing paint (task-567). **And a tired character looks for a
bed** instead of lying down in the road, because a venue lookup exists and reads
the tags the world already had (task-566).

Weather reaches the ground for the first time. `base_temperature` is split from
`temperature` - the world's own climate versus what the simulation is doing - with
a diurnal and seasonal curve on top (task-553). **The engine is the only
month→season table**; two copies in the frontend are gone and a turn is narrated
(task-554). A `climate` paint layer makes a painted map cold at one end and hot at
the other, and a world with no climate layer reads exactly what it read before
(task-557).

**Three of the ways this project has been losing work are now closed by the same
kind of fix**, which is worth naming because the pattern is the recurring one:
a hand-placed area had no way out of anything (task-528's deferred half), a way
made by the NL editor was invisible to every scope because it had edges but no
properties (d7a5021), and a scope record's `area_ids` mirror disagreed with the
areas' own stamps, so the scope tree and the projection counted different worlds
(d7a5021). In all three, **two places held one truth and only one of them was
written by the path that created it.** That is rule 1 below, caught three times in
one week.

### The three rules that decide the order

1. **One copy of every truth.** Ids key nodes, never names (task-446); one dice
   path (`engine/checks.py`); one depletion rule (task-508); the map art's position
   is derived from the grid and the scope offset, never hand-nudged; a way's
   connectivity is its **edges**, and the properties that cache that are derived,
   never the authority. A second implementation is a bug waiting for a reason to
   disagree - and three of them disagreed this week.
2. **Scale is bounded by attention, never by turn length.** The cheap tier must
   always be a *valid but suboptimal* policy, and LLM calls must never scale with
   `time_per_tick_minutes`. Anything that breaks this is not polish, it is a
   correctness regression.
3. **Document the non-obvious in code and here.** Kilo has repeatedly
   misread these systems because the comments and docs were thin.

### Now - the exit test, and the scale it has to survive (1–2 sessions)

| Task | Why now |
|---|---|
| task-400 Pines vertical slice | The end-to-end proof, and the only thing on this list that proves the rest: paint a region, compile it, load only that scope, walk it in play, commit it - with no engine change. Deliberately small. |
| task-520 canvas scale | Verify the acceptance nobody has re-read: a 16k-cell grid pans and zooms, the route tool reports cells · turns · hours, a route paints in one request with one undo entry. |
| task-397/398 projection and generation | In progress. The projection is what task-400 is measured against; the generator is the only sanctioned way to mint an unmade scope. |
| task-527 graph steady-state perf | Re-scope before starting. **bug-510 landed the same day this file first called for it** - Map mode now persists and nodes land on the background - so the premise ("a compiled zone in Map mode is unusable") is half-fixed, and what remains is one measurement: whether label LOD and the Names toggle are sufficient. Not a profiling phase. |

**Landed from this section:** 568, 564, 525, 529, 535, 536, 553, 554, 557, 567,
566, and bug-48 (the fix was already in the code; what was missing was the
acceptance and a unit test, and both now exist).

**Exit test unchanged:** paint a big zone, compile it, load only that scope, walk
it in play, commit it - with no engine change.

### The audits changed the order

Two passes over the tree this week - one reading every todo task in four
clusters, one walking the running app and filing what it saw - turned up more
than they cost, and three things in them outrank most of the table above.

**Four pairs of tasks would undo each other.** Each needs one line saying which
wins before both get done:

- **task-352 vs task-409.** 409 *decided* actions-per-turn is emergent, not
  budgeted, and tests assert the credit model cannot return. 352 reintroduces
  fixed per-tier slots and admits it is "a partial reversal of one line" of that
  decision.
- **task-473 vs task-504 (done).** 504 says in terms that `quantity` must not be
  folded into `uses`. 473 proposes exactly that, filed the day after.
- **task-489 vs task-215.** 215 cancelled numeric opacity and friction by user
  decision; 489's whole goal is to add them back.
- **task-533 vs task-437.** Both decide who owns the turn order - the frontend
  bookkeeper or the engine - and 533 pins an acceptance test on the exact loop 437
  restructures.

**Three tasks are the cheapest real work in the tree**, and none of them is the
biggest:

- **task-599** (with bug-513) - dead interest tags in the library *and* in saves.
  Cheapest item filed, and it makes an **already-shipped** mechanic
  (`interest_tags` → room attention list, auto-dress) actually fire.
- **task-601** (merging bug-512 into it) - the tag-id charset. The most
  load-bearing card in the tree and the worst filed: `priority: low`, no
  acceptance, `Related:` empty, while task-600, task-599 and bug-512 all wait on
  its answer. Validating ids against a charset that is about to change builds the
  validator twice.
- **task-600** - nothing authors the structured personality shape, so
  `likes`/`dislikes`/`fears`/`kinks`/`turn_offs` are wired, tested and
  unreachable. The inspector's Generate button is the authoring path and currently
  asks for prose, which is why it produces a mediocre persona.

**One card in `todo` is already done** and costs attention to re-read: task-405
(implemented and verified 2026-09-19 - the LLM inspector, which now labels all
seventeen of its call sites, task-593). task-218 joined it in `done` on
2026-09-30, but only after its extraction was verified *running* - 16 of its 18
extracted functions instrumented live across a human turn and an NPC reactive
turn. The two that never fire are dead exports (`parseObservation`,
`parseDecisionWithSpeech` - zero call sites, and `git show 170d5f1` proves they
were never called from the engine either), filed as task-657.

**Twenty-odd new cards came out of walking the running app**, and the
simulation-correctness ones belong on this page rather than in a tree:
task-602 (aimed attacks silently drop the region when the phrase carries an
article), task-604 and task-607 (`defense` is one number doing two jobs, and
damage reduction is flat subtraction rather than a percentage), task-608
(derived values render identically to authoritative ones), task-609
(state-area-presence holds five entries for 23 players and disagrees with the
player model), task-605 and task-606 (size is not a real character property, so
ability scores are tier-blind). None is infrastructure; each is a rule the
simulation gets wrong.

### Also in flight, on other threads

- **Soak telemetry and the lived log** (task-542/543 review, 544 in progress):
  the measurement instrument the long-horizon work needs.
- **The character model** (task-534 in progress, 545–547 todo): health and
  vitals with real max HP, hit dice and armour class; recording *which region*
  raised stimulation; frustration when it leads nowhere.
- **Items** (task-537): a spell-effect and condition catalogue review list -
  which reads as work, delivers none, and delays the one entry in it that is
  actually load-bearing. It should be trimmed to that entry.
- **Simultaneous rounds** (task-533): the turn pipeline that never ran - after
  reconciling with task-437 above, which the new turn-system chapter makes
  decidable.

### Next - the simulation contract debt (2–3 sessions)

| Task | Why |
|---|---|
| task-436 action durations / retire action-cost time | The last of the old per-action time model; the timeframe-and-flow rule is the model everything else assumes. |
| task-437 turn-order source of truth | Three passes iterate different orders today; the order is world state and must be resolved once, seeded, and keyed by id. **Also owns the task-533 decision.** |
| task-477 combat + grapple on the central checks | Combat still rolls bespoke; it must inherit ability mods, condition advantage/disadvantage and the degree ladder (task-472 follow-up). Also the natural home for task-538's armour class, which 538 defers to "its own task" and which **no such card currently exists**. |
| task-482 timeskip follow-ups | Long spans, leisure vendors, the explore frontier - the soak tier's remaining reach. Its stated blocker (task-398) has landed; the criterion is stale. |
| task-475 gaps | `npc_behaviors` still calls `move_to_area` directly; no `swim`/`force` verb yet. |
| task-414 batch time advance | The non-blocking human turn, so a timeskip never freezes other players. |

**Exit test:** a full day at 1 and 15 min/tick produces the same decisions and
the same damage, and no mechanic has a second implementation.

### Next - items & inventory depth (2–3 sessions)

| Task | Why |
|---|---|
| task-492 item action model (reach/take/gate/depletion/components) | The reference the camp gear is authored against - after task-508 settles the depletion contract, or it is stale on arrival. |
| task-504 quantity + pooled resource nodes | Bushes hold N berries; each unit has a use count. **Done**; it is what task-473 and task-518 must not re-decide. |
| task-509 library batch triggers | Author the depletion/consume triggers at library scale, not by hand. Blocked on 508 in prose only - say so in frontmatter. |
| task-513 goblin gear spec-driven batch | The camp's actual loadout. |
| task-514/516 provenance and concealment | Who picked it up, who may see it. One of them should own concealment and the other reference it; both currently ask the same question. |
| task-517/519 recreation and starting loadouts | Round out what a character can carry and use. |
| task-450 duplicate instances | The carried/equipped invariant. **bug-509 shares its edge invariant** and a load-time normaliser would mask that symptom without fixing `drop_item`. |

### Then - scale & knowledge (the big one)

Scope-driven promotion (task-710; the attention / awareness-channel model,
task-411 / task-418, is cancelled), the relational spatial model
(task-419), **fog of war (task-499 - the module and its tests are done, the
*wiring* is not: nothing outside `tests/test_fog.py` imports `engine/fog.py`, no
route serves `fog_view`, and no gameplay code writes `player.known`, so the
registry only ever holds what a scenario hand-authored. Treat the remaining work
as "wire task-499 up", not "build fog")**, zone-driven fidelity (task-500), storey
sightlines (task-498), chunk persistence (task-401) and the projection benchmark
(task-402, which duplicates 401's last acceptance line and should be folded into
it). Characters: canonical character nodes (task-457), id-first identity
(task-446), nicknames (task-447), structured appearance/personality (task-507).

**The chunk pipeline has an order that exists only in prose**: 581 (stable ids and
one authoritative location) → 582 (chunk load/unload/merge) → 583 (global index,
gateway ways) → 584 (cross-chunk ownership). Put it in frontmatter or it will be
built in the wrong order.

### Then - UI & tooling

Library browser overhaul (task-510), expression pack (task-512), the help-center
audit (task-521 - half its WorldPainter section is already done by task-575), the
trigger-graph overhaul (task-502/388), save/load UX + list perf (task-455/454,
which currently disagree about the same dialog row), and Playwright persistence
(task-444). The graph toolbar redesign, the contextual scope bar and the
narrow-window overflow menu have landed (task-530/531/532).
**Landed:** task-592 - the scope hierarchy is now the *top of the Outline tab*, so
world → scope → area is one tree in one place instead of three ways to pick a
scope and a tree at the bottom of the graph. task-558 - long edge labels wrap, and
the edge length is computed from the wrapped line count so a wrapped label cannot
overlap the nodes at either end. task-405 - the LLM inspector, now labelled at
every call site so "the inspector is empty" and "the inspector shows seventeen
identical entries" are distinguishable from working.

### The sub-400 sweep - triaged 2026-09-30, and what is left to build

A pass over every card numbered under 400 still sitting in `todo`/`inprogress`
found twelve. Three are now closed on live-browser evidence (task-218, task-376,
task-338). Of the rest, **four should not be built at all** and only five are
real work - which is worth writing down, because four of them look like work.

| Card | Verdict |
|---|---|
| task-215 environmental + clothing effects | **Cancel.** This file already decided it: *"215 cancelled numeric opacity and friction by user decision; 489's whole goal is to add them back."* Building it re-litigates a user decision. |
| task-352 action economy tiers | **Blocked on a decision, not on work.** *"409 decided actions-per-turn is emergent, not budgeted, and tests assert the credit model cannot return; 352 reintroduces fixed per-tier slots and admits it is 'a partial reversal of one line'."* One sentence decides it; building first means building twice. |
| task-99 area grids + movement costs | **Deferred by the user** on 2026-09-30 as large and possibly not needed. Not on any critical path; keep parked. |
| task-83 code readability refactor | **Not a unit of work.** It is the boy-scout rule ("apply when touching files for other reasons"), so it has no acceptance and cannot be done or failed. Leave it as policy. |
| task-299 long-distance communication | **Blocked.** Design approved, MVP unstarted, waiting on task-491/493/494 - all still todo. Starting it now means inventing a contract those three are about to define. |

That leaves five buildable cards. Order, and why:

1. **task-313 relative facing map.** Self-contained gameplay rule, an 181-line
   spec, no new storage format, and one browser session proves it. It is the
   best ratio of demonstrated behaviour to risk in the remaining set.
2. **bug-54 weather is invisible to the engine.** Small, and it is correctness
   rather than polish: `weather_light_multiplier` has no readers and compiled
   areas carry no `outdoor`/`exterior` tag, so weather cannot affect anything.
   Fixing it also settles the outdoor/exterior tagging question that task-313's
   facing work and the environment cards both lean on.
3. **task-289 + task-317, decided as one.** Both describe the same
   template-link contract from two directions (generic sync, then bidirectional).
   Doing them separately is how two sources of truth get created - rule 1.
4. **task-290 template variants**, once 289/317 have fixed the contract.
5. **task-332 legacy item effect props → triggers**, then **task-388** with
   task-502 as one UI session.

**A decision this sweep makes cheaper.** task-533 vs task-437 (who owns turn
order - the frontend bookkeeper or the engine) was one of the four contradictory
pairs above, and it was hard to adjudicate while the turn semantics lived only in
code. They are now written down in
`docs/virtualWorld/Gameplay/Turn Queue & Human Turns.md` and in the AGENTS.md
turn-system block: the queue is **client-side state on the AgentEngine
instance**, rebuilt by `initialize()`/`reconcile()`, and all three "whose turn
is it" indicators project it. That is the fact 437 needs, so the pair can be
decided from the page instead of from memory.

### Always-on hygiene

- **Drain review.** 177 tasks sit in review - more than the todo list. A dedicated
  drain session keeps the folder honest rather than letting review become a second
  todo.
- **Re-read stale tasks before acting.** Three in this revision's audit were decided
  against or already done: task-405 (done, still in `todo`), task-489
  (superseded by 215), task-482 (blocked on something that landed). task-218 was
  the fourth and is now moved.
- **A card is not closed until it has been seen working.** task-218 sat in `todo`
  for seven weeks on the strength of a "Done" line in its own body. It was real
  work, but two of its methods had no caller and nothing had run the refactor
  in a browser. Files existing is not behaviour. Prefer driving the mechanism and
  screenshotting the result over reading a status field.
- **A test that asserts a number the content can change is a test that will
  break.** Two of this week's failures were that: a forage test asserting one draw
  of exactly three ids when the food pool was three, and a hardcoded `80 - 45`
  relief for whichever item was drawn. Both now assert the *property* - whatever
  is drawn is tagged `food` and authors a real effect - which survives the library
  growing under it.
- **Write properties, not members, into tasks that enumerate content.** A task
  listing the exact set of ids or the current value of a constant goes stale the
  next time anyone adds one.
- **`docs/design/js-module-index.md` is generated.** Regenerate with
  `python tools/js_module_index.py --write` after adding a module, and never hand
  it into a commit that does not include the modules it names.
- **JS unit tests: 465 passing, none failing.** The 13 long-standing
  `test_plan_tracker.js` failures are gone.

### Risks to watch

- **The review backlog hides real debt.** 177 review tasks against 125 todo; if it
  is not drained, "done" stops meaning done.
- **Contradictory pairs get done, not decided.** Four pairs are live now. Each was
  filed by someone reasoning correctly from a document that had since changed, and
  that is exactly why they survive review - nothing looks wrong with either task
  alone.
- **Performance is not the first proof.** task-400 is deliberately small - do not
  let a vertical slice turn into a million-node benchmark, and do not let
  task-527's re-scope turn back into a profiling phase.
- **A committed scenario is not a committed model.** `data/scenarios/*` moves fast
  while the author paints; it is content, so it should ride its own commit rather
  than a code change's. **It is also the file most likely to be overwritten by a
  runtime save** - the Kraktooth campaign lost its `name` and all 23
  `character_<slug>` alias nodes to one at 20:28 on the 29th, which is two
  failing tests and a hand-merge away from recovery
  (`git show HEAD~1:data/scenarios/kraktooth_goblin_camp.json`).


## Part 2 - The simulation substrate (audited against the code)

What must be built for the virtual world to be a living, populated, procedurally
populated world - and in what order, because the order is forced by three
verified dependencies.

*Audited 2026-09-27 against the code, not the task tree. Every claim below cites
`file:line`. Part 1 covers the WorldPainter authoring epic; this part covers the
simulation substrate. **Counts re-based 2026-09-30**
against the folders after 0369ef4; the layer claims are still the 09-27 audit and
are marked where they have moved.*

### The short version

**Livesim is done. Do not spend another session on it.** The population
lifecycle, three-tier fidelity model, background simulation, promotion/demotion,
soak orders and timeskip controller-swap are all implemented, seeded, tested and
persisted. The instinct to build livesim next is the most expensive mistake
available right now.

**The actual missing core is the biome→resource consumer.** ~375 lines of
authored, validated, per-biome weighted resource data exist at
`data/worldpainter/biomes.json:1818` and **no code in the engine ever reads
it.** The declaration end is 100% built; the consumer end is 0% built. That is
the single cheapest large win in the repository - and it is still the cheapest,
three days later, which is the most damning sentence in this file. It needs
task-571 (the item-affinity vocabulary) first, and task-571 has an empty
`Related`, so nothing enforces that order.

**Order matters because three things block it**, and they block each other in a
fixed sequence: name-keyed serialization silently destroys data at scale →
non-determinism makes "procedural" meaningless → the compiler has a superlinear
path that dies on exactly the noisy paint a generator produces.

### Where the work actually is

382 open cards. **`review` (272) is larger than `todo` (92)**, so the queue
overstates the backlog and understates the done-ness. The `review` pile is
mostly UI polish; the architectural risk is concentrated in a handful of ids.

| Area | Open | Shape |
|---|---|---|
| ui | 62 | 36 in review, mostly polish - not where the risk is |
| gameplay | 51 | 29 done of 80; genuinely half-built |
| world | 32 | **18 done of 50** - still the least-finished, but no longer nearly empty |
| characters | 31 | 56 done; healthiest area, and the one with the cheapest live win (task-599) |
| graph | 32 | scope fetch + signature dedup landed; virtualisation missing |
| items | 26 | model mature, *content* and *biome wiring* missing |
| triggers | 18 | feature-complete, O(n) scans |
| library | 16 | the "unified registry" is 7/23 built |
| refactor | 11 | mostly shovel |
| bugs | 10 | 40 fixed; the open ones are worth reading |
| environment | 9 | 26 done; weather now reaches a painted map (task-553/554/557) |

**What moved since the 09-27 audit**, so the layer claims below can be read
against it: the WorldPainter epic's floor-plan language landed (task-568's 53
indoor rooms, task-564 per-kind merging, task-525's climb gate, task-529's entry
phrases, task-535's promotion, task-536's rail, task-567's 30 interior plans),
weather reached the ground (553/554/557), venues exist so a tired character walks
to a bed (566), and the two-copies bugs closed (d7a5021).

### Layer 0 - Identity (blocks every world-scale task)

`task-446` is ~60% done. The good half is real: opaque `Player.id`
(`player.py:97`), both player indices and `reindex()` (`player_manager.py:24-43`),
`relationship_key()` (`player_manager.py:65-94`), `NodeIDHelper` prefixes
(`node_ids.py:16-52`). The bad half is still open:

- **Serialization keys areas by display name** - `serialization.py:216`
  `rooms_serialized[node.name] = {...}`. Two "kitchen" areas in different scopes
  **silently overwrite each other in the save file**. This is data loss, not a
  performance issue, and it gets worse the more scopes exist.
- **`Player.current_area` is a display name** - `player.py:219`, serialised
  as-is at `player.py:724`, with **47+ references across 10 files**
  (`tick_manager.py:466`, `npc_behaviors.py`, `movement.py`, `lighting.py`,
  `sound.py`, `proximity.py`, `combat.py`, `area_description.py`,
  `player_ops.py`) resolving it back to an id each time.
- **`WorldGraph.load_from_dict` is clear-and-replace** - `graph.py:261-268`.
  No merge API exists, so chunk loading (task-401) cannot be written.

8 of the 9 claims in `dev_tasks/critical-review-scale-2026-09-08.md` are
**still true 19 days later**. Only the editor's scope-scoped fetch was partly
addressed (`static/js/graph/network-manager.js:359-376`, with a full-graph
fallback still present).

**Do:** `current_area` → `current_area_id`; serialise `areas` by `node.id`; add
`WorldGraph.merge_chunk()`.

**Exit test:** two areas with the same name in different scopes survive a
save/load round trip intact, and a character can cross a chunk boundary.

### Layer 1 - Determinism (prerequisite for the word "procedural")

There is a central dice path - `engine/checks.py:87` `roll_dice` - and most
subsystems correctly seed themselves. But **17+ call sites use the bare
`random` module with no seed**, which makes a session unreplayable:

`combat.py:326` (stun) · `npc_behaviors.py:189,216,369,398,475` (wander, dialog,
direction) · `area_statuses.py:245` · `body_parts.py:329` (injury location) ·
`crafting.py:185` · `environment_propagation.py:233,235` · `narration.py:305` ·
`items/transfer_actions.py:151-152` · `tick_manager.py:896,911` ·
`triggers/condition_tree.py:160` · and two *time-based* trigger-id generators
(`trigger_system.py:89`, `serialization_template.py:189,237`).

This matters beyond tidiness. Layer 3 generates a world procedurally, Layer 2
benchmarks it, and the soak telemetry (`engine/soak_telemetry.py:101-106`)
measures it. **If the NPCs roll unseeded dice, none of those measurements mean
anything.** `engine/soak_runner.py:496-501` already demonstrates the correct
save/restore pattern; it is only used for soak tests.

**Do:** one `random.Random(seed)` created at world init, threaded to every
subsystem; replace the bare calls; seed trigger ids.

**Exit test:** the same seed produces a byte-identical trace over N ticks.

### Layer 2 - Compiler scale (the thing that dies first)

The grid compiler `engine/world_compile.py:1087 compile_grid` is linear apart
from one path: `_nearest_cells` (`:1036-1062`) runs a **full-grid BFS per
disconnected component**, driven from `:1862-1866`. That is **O(C × W × H)**.
With `region_merge=False` on a noisy biome paint - precisely the shape a
procedural generator produces, since each differently-painted cell becomes its
own region - C approaches the cell count. A 200×200 checkerboard is ~20,000
components × 40,000 cells.

The only shipped evidence is **1,350 cells** (`data/scenarios/kraktooth_goblin_camp.json:29171`),
and `routes/world_grid_ops.py:1038-1044` carries a hard `max_nodes = 20000`
choke with a comment admitting the problem. **No benchmark exists.** `task-402`
asks for one and is still `todo`.

**Do:** index the component→cell adjacency instead of re-BFS; add the task-402
benchmark; only then raise or remove `max_nodes`.

**Exit test:** a 200×200 procedurally painted region compiles in bounded time,
with a committed measurement.

### Layer 3 - Biome resources: the actual missing core

This is the thing worth doing next, and the reason is unusually favourable.

**What exists.** `data/worldpainter/biomes.json:1818-2194` is ~375 lines of
authored, per-biome weighted resource data, e.g.:

```json
"sparse_forest": [
  { "tags": ["berry","fruit"], "weight": 4 },
  { "tags": ["herb","medicinal"], "weight": 3 },
  { "tags": ["root","food"], "weight": 2 }
]
```

`hostile_distribution` (`:2195+`) is the same shape with `base_chance`,
`per_area_from_settlement`, `max_chance`.

Both are loaded (`engine/biomes.py:131-136`) and both are **fully validated**
(`engine/biomes.py:397-439`, covered by `tests/test_biomes.py`).

**What does not exist: any consumer.** A repo-wide grep for
`resource_distribution` returns the data file, the loader, the validator, the
tests, and one mention in a task writeup. Nothing else. `HOSTILE_KINDS`
(`engine/biomes.py:41`) appears nowhere outside that file and its tests.

**Why the chain is broken in the middle, precisely:**

| Link | State |
|---|---|
| biome → area node tags | **REAL** - `world_compile.py:1451-1459` |
| area tags → foraging chance/flavour | **REAL** - `foraging.py:424-427, 360-375` |
| area tags → population engine | **REAL but inert** - `population_ops.py:65,88` reads tags, but only an explicit HTTP call reaches it, and it returns `{"status":"empty"}` for wilderness |
| **biome distribution → items** | **DOES NOT EXIST** |

That last row is the whole gap. Supporting evidence:

- **`compile_grid` emits zero item nodes.** Its area property set
  (`:1463-1484`) is `tags, floor, surface, environment, description, x, y, cell`
  - no items key, and no call to `population.py` anywhere in the function.
- **No paint layer for items.** `PAINT_LAYERS = ("biome","road","floor","climate")`
  (`world_grid.py:102`); the vocabulary endpoint serves only those four
  (`world_grid_ops.py:266-294`) and does not even expose the distribution tables.
- **The two vocabularies never meet.** I grepped every file in
  `data/library/items/` for the wilderness biome tags - `forest`, `woods`,
  `rocky`, `farmland`, `shore`, `ruin`, `road`, `dense` → **zero matches**. The
  only bridges are `storage`, `trade`, `religious`, all from *building* biomes.
  So a compiled forest yields an empty plan.
- **Every wilderness library area is empty.** 89 areas, 51 with authored items,
  38 with `"items": []` - and the empties are `deep_forest.json:16`,
  `northern_hills.json:16`, `blackmarsh.json:17`, `human_road.json:16`,
  `old_dwarven_ruins.json:17`. Only interiors are stocked.
- **No loot table, spawn weight, drop chance, or rarity exists anywhere.**
  Repo-wide grep for `loot_table|drop_chance|spawn_weight|rarity` → three prose
  hits, zero code. The only weighted tables are skill-keyed
  (`data/library/foraging.json`) and biome-keyed-and-dead.
- **No item↔biome affinity field.** No biome can say "this item belongs here".
- **`quantity` appears nowhere in `engine/`.** Without it (task-504) a thicket
  cannot yield copies and shrink.
- **The forage pool is 12 items** - only 12 library files carry the `forage` tag.
- **`GenerationReport.unresolved_tags`** (`generation.py:48`) is a field built
  precisely for "I asked the library for tag X and it offered nothing", and
  **no recipe ever populates it.** It is the hook this work needs.
- **`lint_library.py` never opens `biomes.json`.** Its only area-adjacent check
  is `area_tag_gaps` (`:223-229`), which asks whether an area has *any* tags -
  not whether the tag vocabulary meets the biomes.

**One warning about the task tree.** `task-497` is filed **done**, and its
acceptance criteria read as behaviour: *"Resource distribution rules exist
(biome → likely items)"*. Its own progress note is honest - *"Delivered as a
data file plus a generic loader/validator; no engine behaviour change"* - but
the closure is optimistic. **Any plan that reads task-497 as "biome resources
ship" is wrong.** Trust the code, not the folder.

**Do, in this order:**

1. Add a biome-affinity field to library items (the missing vocabulary bridge).
2. `task-504` - `quantity` and pooled resource nodes, so a thicket yields
   copies and shrinks. This is the data model everything else needs.
3. A spawner that reads `resource_distribution` and places items into compiled
   areas, populating `unresolved_tags` when a tag resolves to nothing.
4. Widen the forage pool beyond 12; make regrowth an engine model rather than a
   hand-authored trigger idiom (`bush_of_berries.json:18-69` does it by hand).
5. Extend `lint_library.py` to open `biomes.json` and report every biome with no
   reachable item.
6. Make the `population` route chain off generation so wilderness populates
   without a manual click.

**Exit test:** paint a forest, press Generate, and the forest contains berries
and herbs in the proportions `resource_distribution` specifies; the thicket
shrinks as it is harvested and regrows; two runs from one seed are identical.

### Layer 4 - Hostiles, and the wilderness vocabulary

Same shape as Layer 3, but it needs Layer 3's spawner first. Also blocked by
the vocabulary gap above: `plan_population` is correct code fed the wrong words,
which is why it returns empty for every non-interior area.

### Layer 5 - Time and turn order

The clock is a single source (`virtual_world_engine.py:1004-1015`; ticks ×
`time_per_tick_minutes` + clock start) and every action costs 1 minute
(`tick_manager.py:149-150`). That part is coherent.

Two gaps remain: there is **no turn-order source of truth** (`task-437`) -
ordering is an accident of dict insertion order - and no central action-duration
registry (`task-436`). Both block simultaneous mode (`task-533`) and any
multi-character fairness claim.

### Layer 6 - Trigger indexing (scale, not features)

The trigger system is the most complete subsystem in the repo: **23 trigger
types, 41 effect types, 58 conditions**, plus a real static validator
(`trigger_validator.py:165-832`). Do not rebuild it.

But `execution.py` resolves targets by scanning the whole graph -
`:29`, `:47`, `:198`, `:203`, `:228`, `:253` - and `get_edges_for_source` is a
linear scan (`graph.py:130-155`). Every `on_tick` trigger on every item walks
those. Fine at 1,350 cells; a showstopper at 100k. Blocked on graph indexes
(`task-407`).

### Orthogonal - drain the review pile

177 tasks in `review` against 140 in `todo`. Until review means something, every
count in this document is unreliable, and the Roadmap's own note is right that
"if it is not drained, done stops meaning done." Start with the ones the recent
sessions produced, whose acceptance nobody has re-read: task-496, 526, 528,
530, 531, 532, 539, 540, 541, 548, 559, 560, 561, 562, 563, 564, 566, 567, 568
and bug-48…54.

**Architectural risk in that pile is concentrated** in task-407 (edge
indexing), 440 (splitting the 1100-line `virtual_world_engine.py` god object),
442 (trigger blueprint runtime), 480 (skill growth), 495 (recursive scope
grids), 496 (grid→graph compiler), 527 (graph steady-state perf, which now wants
re-scoping) and 567 (the interior generator that turns a plan into paint). The
other ~169 are editor polish and can be triaged cheaply.

**Two of those are now settled and should leave the pile on a re-read rather than
a re-implementation**: 495 and 496 shipped as the WorldPainter epic's compiler and
its authoring loop; 560–568 are the town/floor-plan vocabulary, and their
acceptance is the point of the 2026-09-30 patch notes.

### What not to do

- **Do not rebuild livesim.** It is implemented, seeded, tested
  (`test_promotion.py`, `test_background_simulation.py`, `test_soak_runner.py`)
  and persisted. Its real gaps are narrow and non-blocking: no test for
  `process_simple_npcs` (`npc_behaviors.py:284`) and none for
  `timeskip.run_policy_step` (`timeskip.py:141`).
- **Do not treat "proceed" as verification.** 3,239 tests, but **no integration
  or E2E layer at all** - no save/load round-trip test, no timeskip determinism
  test, no trigger fan-out test, and no perf baseline. The unit tests are
  strong; the seams between systems are untested, and the seams are where the
  remaining bugs are.
- **Do not trust `done`.** task-497 is the counter-example that matters.
- **Do not remove `max_nodes` before task-402 lands.** That cap is currently the
  only thing standing between a noisy paint and a hang.

### Sequence

```
0  identity (task-446 remainder)      ─┐
1  determinism (17 random calls)       ├─ everything below needs these
2  compiler index + benchmark (402)   ─┘
3  biome resource consumer  ◀── the cheapest large win in the repo
4  hostile distribution + wilderness vocabulary
5  time contract + turn order (436/437)
6  trigger indexing (407 -> 512, 527)
   └─ review drain throughout; integration test layer alongside
```
