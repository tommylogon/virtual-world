# Roadmap

Where the world is going, in what order, and why. This is a proposal, not a
promise: it is re-aimed whenever the simulation teaches us something. Part of
[[_Index]].

*Written 2026-09-24, after `e4af71c`. Updated 2026-09-27 after `b885878`; again
2026-09-30 after `0369ef4`, which closed the floor-plan language gap this file
spent two revisions calling the last thing between a plan and a place.*

## Where we are

| Status | Count |
|---|---|
| Done | 381 |
| Review | 177 |
| In progress | 8 |
| Todo | 141 |

(Counted from the folders, which are authoritative — not the frontmatter.)

**A floor plan is now a language, and a painted town is somewhere you live.**
The revision two days ago ended on the gap that blocked everything else: a
building you could enter was a building with nothing to paint inside it, because
`classroom`, `hallway` and `stairway` were unknown ids and a real plan compiled
to bare places plus a warning. That is closed. `data/worldpainter/biomes.json`
carries **53 indoor rooms** across thirteen purposes, plus a `stairway` that is a
*passable* cell and agrees with the stairwell the compiler already minted
(task-568). Merging became per-kind, so a corridor is one corridor whatever the
scope's switch says and a terrace of cottages is three cottages (task-564). A step
past three storeys is refused in words — *"The climb is 6 storeys of bare ground —
you would need a path cut into it"* — and a road painted across it opens the step
(task-525). **A building brings its own interior**: 30 drawn plans covering all 31
building types, painted as cells so the standard compiler builds the rooms and an
author edits them by editing paint (task-567). **And a tired character looks for a
bed** instead of lying down in the road, because a venue lookup exists and reads
the tags the world already had (task-566).

Weather reaches the ground for the first time. `base_temperature` is split from
`temperature` — the world's own climate versus what the simulation is doing — with
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

## The three rules that decide the order

1. **One copy of every truth.** Ids key nodes, never names (task-446); one dice
   path (`engine/checks.py`); one depletion rule (task-508); the map art's position
   is derived from the grid and the scope offset, never hand-nudged; a way's
   connectivity is its **edges**, and the properties that cache that are derived,
   never the authority. A second implementation is a bug waiting for a reason to
   disagree — and three of them disagreed this week.
2. **Scale is bounded by attention, never by turn length.** The cheap tier must
   always be a *valid but suboptimal* policy, and LLM calls must never scale with
   `time_per_tick_minutes`. Anything that breaks this is not polish, it is a
   correctness regression.
3. **Document the non-obvious in code and here.** Kilo has repeatedly
   misread these systems because the comments and docs were thin.

## Now — the exit test, and the scale it has to survive (1–2 sessions)

| Task | Why now |
|---|---|
| task-400 Pines vertical slice | The end-to-end proof, and the only thing on this list that proves the rest: paint a region, compile it, load only that scope, walk it in play, commit it — with no engine change. Deliberately small. |
| task-520 canvas scale | Verify the acceptance nobody has re-read: a 16k-cell grid pans and zooms, the route tool reports cells · turns · hours, a route paints in one request with one undo entry. |
| task-397/398 projection and generation | In progress. The projection is what task-400 is measured against; the generator is the only sanctioned way to mint an unmade scope. |
| task-527 graph steady-state perf | Re-scope before starting. **bug-510 landed the same day this file first called for it** — Map mode now persists and nodes land on the background — so the premise ("a compiled zone in Map mode is unusable") is half-fixed, and what remains is one measurement: whether label LOD and the Names toggle are sufficient. Not a profiling phase. |

**Landed from this section:** 568, 564, 525, 529, 535, 536, 553, 554, 557, 567,
566, and bug-48 (the fix was already in the code; what was missing was the
acceptance and a unit test, and both now exist).

**Exit test unchanged:** paint a big zone, compile it, load only that scope, walk
it in play, commit it — with no engine change.

## The audits changed the order

Two passes over the tree this week — one reading every todo task in four
clusters, one walking the running app and filing what it saw — turned up more
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
- **task-533 vs task-437.** Both decide who owns the turn order — the frontend
  bookkeeper or the engine — and 533 pins an acceptance test on the exact loop 437
  restructures.

**Three tasks are the cheapest real work in the tree**, and none of them is the
biggest:

- **task-599** (with bug-513) — dead interest tags in the library *and* in saves.
  Cheapest item filed, and it makes an **already-shipped** mechanic
  (`interest_tags` → room attention list, auto-dress) actually fire.
- **task-601** (merging bug-512 into it) — the tag-id charset. The most
  load-bearing card in the tree and the worst filed: `priority: low`, no
  acceptance, `Related:` empty, while task-600, task-599 and bug-512 all wait on
  its answer. Validating ids against a charset that is about to change builds the
  validator twice.
- **task-600** — nothing authors the structured personality shape, so
  `likes`/`dislikes`/`fears`/`kinks`/`turn_offs` are wired, tested and
  unreachable. The inspector's Generate button is the authoring path and currently
  asks for prose, which is why it produces a mediocre persona.

**Two cards in `todo` are already done** and cost attention to re-read: task-218
(shipped 2026-08-12) and task-405 (implemented and verified 2026-09-19 — the LLM
inspector, which now labels all seventeen of its call sites, task-593).

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

## Also in flight, on other threads

- **Soak telemetry and the lived log** (task-542/543 review, 544 in progress):
  the measurement instrument the long-horizon work needs.
- **The character model** (task-534 in progress, 545–547 todo): health and
  vitals with real max HP, hit dice and armour class; recording *which region*
  raised stimulation; frustration when it leads nowhere.
- **Items** (task-537): a spell-effect and condition catalogue review list —
  which reads as work, delivers none, and delays the one entry in it that is
  actually load-bearing. It should be trimmed to that entry.
- **Simultaneous rounds** (task-533): the turn pipeline that never ran — after
  reconciling with task-437 above.

## Next — the simulation contract debt (2–3 sessions)

| Task | Why |
|---|---|
| task-436 action durations / retire action-cost time | The last of the old per-action time model; the timeframe-and-flow rule is the model everything else assumes. |
| task-437 turn-order source of truth | Three passes iterate different orders today; the order is world state and must be resolved once, seeded, and keyed by id. **Also owns the task-533 decision.** |
| task-477 combat + grapple on the central checks | Combat still rolls bespoke; it must inherit ability mods, condition advantage/disadvantage and the degree ladder (task-472 follow-up). Also the natural home for task-538's armour class, which 538 defers to "its own task" and which **no such card currently exists**. |
| task-482 timeskip follow-ups | Long spans, leisure vendors, the explore frontier — the soak tier's remaining reach. Its stated blocker (task-398) has landed; the criterion is stale. |
| task-475 gaps | `npc_behaviors` still calls `move_to_area` directly; no `swim`/`force` verb yet. |
| task-414 batch time advance | The non-blocking human turn, so a timeskip never freezes other players. |

**Exit test:** a full day at 1 and 15 min/tick produces the same decisions and
the same damage, and no mechanic has a second implementation.

## Next — items & inventory depth (2–3 sessions)

| Task | Why |
|---|---|
| task-492 item action model (reach/take/gate/depletion/components) | The reference the camp gear is authored against — after task-508 settles the depletion contract, or it is stale on arrival. |
| task-504 quantity + pooled resource nodes | Bushes hold N berries; each unit has a use count. **Done**; it is what task-473 and task-518 must not re-decide. |
| task-509 library batch triggers | Author the depletion/consume triggers at library scale, not by hand. Blocked on 508 in prose only — say so in frontmatter. |
| task-513 goblin gear spec-driven batch | The camp's actual loadout. |
| task-514/516 provenance and concealment | Who picked it up, who may see it. One of them should own concealment and the other reference it; both currently ask the same question. |
| task-517/519 recreation and starting loadouts | Round out what a character can carry and use. |
| task-450 duplicate instances | The carried/equipped invariant. **bug-509 shares its edge invariant** and a load-time normaliser would mask that symptom without fixing `drop_item`. |

## Then — scale & knowledge (the big one)

Attention (task-411), awareness channels (task-418), the relational spatial model
(task-419), fog of war (task-499), zone-driven fidelity (task-500), storey
sightlines (task-498), chunk persistence (task-401) and the projection benchmark
(task-402, which duplicates 401's last acceptance line and should be folded into
it). Characters: canonical character nodes (task-457), id-first identity
(task-446), nicknames (task-447), structured appearance/personality (task-507).

**The chunk pipeline has an order that exists only in prose**: 581 (stable ids and
one authoritative location) → 582 (chunk load/unload/merge) → 583 (global index,
gateway ways) → 584 (cross-chunk ownership). Put it in frontmatter or it will be
built in the wrong order.

## Then — UI & tooling

Library browser overhaul (task-510), expression pack (task-512), the help-center
audit (task-521 — half its WorldPainter section is already done by task-575), the
trigger-graph overhaul (task-502/388), save/load UX + list perf (task-455/454,
which currently disagree about the same dialog row), and Playwright persistence
(task-444). The graph toolbar redesign, the contextual scope bar and the
narrow-window overflow menu have landed (task-530/531/532).

**Landed:** task-592 — the scope hierarchy is now the *top of the Outline tab*, so
world → scope → area is one tree in one place instead of three ways to pick a
scope and a tree at the bottom of the graph. task-558 — long edge labels wrap, and
the edge length is computed from the wrapped line count so a wrapped label cannot
overlap the nodes at either end. task-405 — the LLM inspector, now labelled at
every call site so "the inspector is empty" and "the inspector shows seventeen
identical entries" are distinguishable from working.

## Always-on hygiene

- **Drain review.** 177 tasks sit in review — more than the todo list. A dedicated
  drain session keeps the folder honest rather than letting review become a second
  todo.
- **Re-read stale tasks before acting.** Four in this revision's audit were decided
  against or already done: task-218 and task-405 (done, still in `todo`),
  task-489 (superseded by 215), task-482 (blocked on something that landed).
- **A test that asserts a number the content can change is a test that will
  break.** Two of this week's failures were that: a forage test asserting one draw
  of exactly three ids when the food pool was three, and a hardcoded `80 - 45`
  relief for whichever item was drawn. Both now assert the *property* — whatever
  is drawn is tagged `food` and authors a real effect — which survives the library
  growing under it.
- **Write properties, not members, into tasks that enumerate content.** A task
  listing the exact set of ids or the current value of a constant goes stale the
  next time anyone adds one.
- **`docs/design/js-module-index.md` is generated.** Regenerate with
  `python tools/js_module_index.py --write` after adding a module, and never hand
  it into a commit that does not include the modules it names.
- **JS unit tests: 452 passing, none failing.** The 13 long-standing
  `test_plan_tracker.js` failures are gone.

## Risks to watch

- **The review backlog hides real debt.** 177 review tasks against 141 todo; if it
  is not drained, "done" stops meaning done.
- **Contradictory pairs get done, not decided.** Four pairs are live now. Each was
  filed by someone reasoning correctly from a document that had since changed, and
  that is exactly why they survive review — nothing looks wrong with either task
  alone.
- **Performance is not the first proof.** task-400 is deliberately small — do not
  let a vertical slice turn into a million-node benchmark, and do not let
  task-527's re-scope turn back into a profiling phase.
- **A committed scenario is not a committed model.** `data/scenarios/*` moves fast
  while the author paints; it is content, so it should ride its own commit rather
  than a code change's. **It is also the file most likely to be overwritten by a
  runtime save** — the Kraktooth campaign lost its `name` and all 23
  `character_<slug>` alias nodes to one at 20:28 on the 29th, which is two
  failing tests and a hand-merge away from recovery
  (`git show HEAD~1:data/scenarios/kraktooth_goblin_camp.json`).
