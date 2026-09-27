# Roadmap

Where the world is going, in what order, and why. This is a proposal, not a
promise: it is re-aimed whenever the simulation teaches us something. Part of
[[_Index]].

*Written 2026-09-24, after `e4af71c`. Updated 2026-09-27, after `b885878`.*

## Where we are

| Status | Count |
|---|---|
| Done | 347 |
| Review | 159 |
| In progress | 8 |
| Todo | 110 |

(Counted from the folders, which are authoritative — not the frontmatter. The
previous revision's Done figure of 340 does not match the folder, so the table is
re-based here rather than trusted.)

The **observer-view block is implemented and in review.** Every painted cell is a
place, a road cell replaces its biome, a description composes the place's
*character* from its neighbours and the storey beside it, and feature entries
carry a narrative phrase. The same session closed the authoring gaps that made it
unusable: a hand-written area can be parked on a cell, scope membership is edited
on the node (so a child scope's interior moves wholesale, and stops showing in the
parent), every cell can be read on hover or click, and the place tool's picker is
grouped by scope.

Map drawing then had to be taught to agree with itself. Four bugs, all the same
shape — two sources of truth for one position: art drifting off its grid, a pitch
change splitting the map from its areas, a rename that never reached the picker,
and a zone drag that moved whichever map was selected. **One rule now: the art is
derived from its scope's grid plus that scope's offset, and nothing else.** Node
boxes, item offsets and the solver's spring follow the pitch, so a wide map reads
as a map instead of specks.

The epic still in flight is **WorldPainter → a compiled world**. The compiler and
its authoring loop are done; what remains is making a *big* painted world
comfortable, and proving the whole thing end to end in play.

**A town is now something you can stand in.** The last session closed the gap
between "a grid of coloured cells" and "a place you walk into": a cell can be
*named* (task-560), it can be a *building* of one of 31 typed kinds (task-561), a
cell can be something that is not a place at all — a wall, a window, a door
(task-562) — and a building is entered with `in` from any side that has a way
(task-563), which refuses with a line drawn from its category until something
opens it. Storeys became a whole-number index rather than a material (4467da8), so
merging can no longer fuse a classroom with the one above it, and `map render`
learned to derive its own pitch from the painted extent (task-526). What is
missing is the vocabulary to write a floor plan with — `classroom`, `hallway`,
`stairway` are still unknown ids that compile to bare places with a warning.

## The three rules that decide the order

1. **One copy of every truth.** Ids key nodes, never names (task-446); one dice
   path (`engine/checks.py`); one depletion rule (task-508); the map art's position
   is derived from the grid and the scope offset, never hand-nudged. A second
   implementation is a bug waiting for a reason to disagree.
2. **Scale is bounded by attention, never by turn length.** The cheap tier must
   always be a *valid but suboptimal* policy, and LLM calls must never scale with
   `time_per_tick_minutes`. Anything that breaks this is not polish, it is a
   correctness regression.
3. **Document the non-obvious in code and here.** Kilo has repeatedly
   misread these systems because the comments and docs were thin.

## Now — make the big painted world comfortable (next 1–2 sessions)

| Task | Why now |
|---|---|
| task-526 map scale rendering | **Landed (review).** The pitch is derived from the painted extent (a 20×9 zone gets 80px/cell, a 200×133 world 30px) with the stepper as a visible override, and below 140px/cell areas draw as cell-sized dots with no name — the cards overlapped because a card's width is its *name*, which never shrank. The pitch now scales the drawing at both ends, so this was the last piece of "a big map reads well". |
| task-560/561 towns: named, typed cells | **Landed (review).** A cell can be named (a `names` map beside the layers, because a name is metadata and not paint) and the compiler prefers it, with the duplicate-inside-a-scope fallback so no area offers two exits with one name. 31 building types across 9 categories as *biomes* (they used to be features, which made a house compile as a road), each tagged with a category and its purposes — the hook task-566 needs. |
| task-562 edge semantics | **Landed (review).** A cell can be something that is *not* a place: `wall`/`void` block, `window` sees through but does not pass, `door` is a threshold — declared in the vocabulary (`biomes.cell_kind`), so the compiler asks rather than hardcoding. Every way carries `kind` (open/door/stairs/entrance) and `floor_step`, so a storey step reads as a climb and task-525/563 have a number to read. A wall blocks by occupying a cell, so a floor plan finally means what it says; merging is now storey-aware, since a classroom above a classroom was becoming one place with a staircase in it. |
| task-563 entering a building | **Landed (review).** A building is a place you go *into*: one `in` way per cardinal side that already has a way, so you type `in` from the street instead of stepping onto the doorstep. With an interior it leads there (one-way, so `out` inside keeps meaning the doorstep and the adjacent temple is one turn); with no interior it is a `closed` door carrying a themed `refusal_message` — a watch house is barred, an inn is shut — which the movement system honours until the state is `open`, so a knock or a key opens it later. `refusal_message` is a general way property, not a building hack; a plain `closed` door still opens on approach as before. |
| task-568 an indoor vocabulary | A building you can enter is somewhere you can be *in*, and there is still nothing to paint it with: `classroom`, `hallway`, `stairway`, `corridor`, `kitchen` are unknown ids, so a real floor plan compiles to bare places plus a warning. The 31 building types imply the rooms; the rooms are the last thing between a plan and a place. |
| task-527 graph steady-state perf | Profile and fix the main-thread drag on a large painted map (labels/edges/redraw). Measured, not guessed — a previous hypothesis was wrong. |
| task-400 Pines vertical slice | The end-to-end proof: a painted region compiled, walked, and trusted. Small on purpose. |
| task-398 deterministic structure generation | The generator is the only sanctioned way to mint an unmade scope, and it must be reproducible and editable after the fact. |
| task-397 world scopes | Finish the projection so the editor/runtime can address a zone without inventing a second spatial model. |
| task-520 canvas scale (review) | Verify the acceptance: a 16k-cell grid pans/zooms, the route tool reports cells · turns · hours, a route paints in one request with one undo entry. |
| task-525 storey-delta traversal gate | The compiler now writes `properties.floor` as a **storey index** (0 ground, 1 up, -1 down, unbounded — an 80-storey tower, a lake bottom at -2, -900 in a hole to hell) and the prose reads it; the ground material moved to `properties.surface`. A step past ~3 storeys should require a climb (and may block the step). The data exists — the gate does not. |
| task-529 the last third of feature entries | The phrase is carried by the edge and resolves in both directions (landed with task-496), but the *area description* does not yet offer it ("a cave mouth yawns here; you could enter"). |
| task-535 promote a selection into a child scope | The membership move landed (task-539); turning a *selection* into a new zone with a gateway is the remaining half. |
| task-536 WorldPainter tool rail | Marquee cell selection and moving a painted selection, so a region is edited as a region. |

**Exit test:** paint a big zone, compile it, load only that scope, walk it in
play, commit it — with no engine change.

## Also in flight, on other threads

Not part of the sequence above, but they change what the world can be asked to do,
so they are named here rather than lost in the task tree:

- **Soak telemetry and the lived log** (task-542 review, 543 review, 544 in
  progress): the trace/soak split, presence intervals and an action-stream
  capture, and a space-time swimlane view. This is the measurement instrument the
  long-horizon work needs.
- **The character model** (task-534 in progress, 545–547 todo): health and vitals
  with real max HP, hit dice and armour class; recording *which region* raised
  stimulation; frustration when it leads nowhere; who saw whom this turn.
- **Items** (task-537): a spell-effect and condition catalogue review list, with
  the effect handlers and library items landing alongside it.
- **Simultaneous rounds** (task-533): the turn pipeline that never ran, and the
  End-round control.

## Next — the simulation contract debt (2–3 sessions)

| Task | Why |
|---|---|
| task-436 action durations / retire action-cost time | The last of the old per-action time model; the timeframe-and-flow rule is the model everything else assumes. |
| task-437 turn-order source of truth | Three passes iterate different orders today; the order is world state and must be resolved once, seeded, and keyed by id. |
| task-477 combat + grapple on the central checks | Combat still rolls bespoke; it must inherit ability mods, condition advantage/disadvantage and the degree ladder (task-472 follow-up). |
| task-482 timeskip follow-ups | Long spans, leisure vendors, the explore frontier — the soak tier's remaining reach. |
| task-475 gaps | `npc_behaviors` still calls `move_to_area` directly; no `swim`/`force` verb yet. |
| task-414 batch time advance | The non-blocking human turn, so a timeskip never freezes other players. |
| task-506 author consumption on library food/drink | Then `MEAL_RESTORE`/`DRINK_RESTORE` and the whole fallback branch can be retired (task-508 was the blocker). |

**Exit test:** a full day at 1 and 15 min/tick produces the same decisions and
the same damage, and no mechanic has a second implementation.

## Next — items & inventory depth (2–3 sessions)

| Task | Why |
|---|---|
| task-492 item action model (reach/take/gate/depletion/components) | The reference the camp gear is authored against. |
| task-504 quantity + pooled resource nodes | Bushes hold N berries; each unit has a use count. |
| task-509 library batch triggers | Author the depletion/consume triggers at library scale, not by hand. |
| task-473 stacks, task-450 duplicate instances | Grouped world items without losing identity. |
| task-514/515/516 provenance, ownership, concealment | Who picked it up, who may take it, what is hidden. |
| task-513 goblin gear spec-driven batch | The camp's actual loadout. |
| task-517/518/519 recreation, ranged, starting loadouts | Round out what a character can carry and use. |

## Then — scale & knowledge (the big one)

Attention (task-411), awareness channels (task-418), the relational spatial model
(task-419), fog of war (task-499), zone-driven fidelity (task-500), storey
sightlines (task-498), the storey-delta traversal gate (task-525), chunk
persistence (task-401) and the projection benchmark
(task-402). Characters: canonical character nodes (task-457), id-first identity
(task-446), nicknames (task-447), the life-experience generator (task-404),
structured appearance/personality (task-507).

## Then — UI & tooling

Library browser overhaul (task-510), expression pack (task-512), the help-center
audit (task-521), the trigger-graph overhaul (task-502/388), save/load UX + list
perf (task-455/454), and Playwright persistence (task-444). The graph toolbar
redesign, the contextual scope bar and the narrow-window overflow menu have landed
(task-530/531/532); what is left there is **bug-48** — the map layout is silently
ignored while Levels owns the layout.

## Always-on hygiene

- **Drain review.** 159 tasks sit in review — more than the todo list. A dedicated
  drain session keeps the folder honest rather than letting review become a second
  todo. Start with the ones this session produced (task-496, 526, 528, 530, 531,
  532, 539, 540, 541, 548, 559, 560, 561, 562, 563 and bug-49…54), since they are
  the ones whose acceptance nobody has re-read yet.
- **13 pre-existing JS unit failures** (`test_plan_tracker.js`) — fix or delete
  the stale expectations.
- **Stale tasks must be re-read against the current design before acting**
  (task-409's action-budget blocker is retired; task-475's gaps are recorded in
  code; task-529's acceptance was still literally "TODO" while most of it had
  already landed inside task-496).
- **`docs/design/js-module-index.md` is generated.** Regenerate it with
  `python tools/js_module_index.py --write` after adding a module, and never hand
  it into a commit that does not include the modules it names.

## Risks to watch

- **The review backlog hides real debt.** 159 review tasks is bigger than the todo
  list; if it is not drained, "done" stops meaning done.
- **Performance is not the first proof.** task-400 is deliberately small — do
  not let a vertical slice turn into a million-node benchmark.
- **A committed scenario is not a committed model.** `data/scenarios/*` moves fast
  while the author paints; it is content, so it should ride its own commit rather
  than a code change's.
