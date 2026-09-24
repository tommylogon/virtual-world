# Roadmap

Where the world is going, in what order, and why. This is a proposal, not a
promise: it is re-aimed whenever the simulation teaches us something. Part of
[[_Index]].

*Written 2026-09-24, after `e4af71c`.*

## Where we are

| Status | Count |
|---|---|
| Done | 340 |
| Review | 140 |
| In progress | 8 |
| Todo | 83 |

The last pass landed the **WorldPainter** grid surface and world scopes
(`fa2bb48`), kept a character's appearance in step with visible state
(`82fc602`, task-486), gave `eat`/`drink` one depletion rule (`caf663d`,
task-508), and filed the task moves (`e4af71c`).

The epic in flight is **WorldPainter → a compiled world**: paint a grid, compile
it into real areas and ways, and let the graph load one scope at a time. The
payoff is a world large enough that the *attention* model — not the node count —
is the limit.

## The three rules that decide the order

1. **One copy of every truth.** Ids key nodes, never names (task-446); one dice
   path (`engine/checks.py`); one depletion rule (task-508). A second
   implementation is a bug waiting for a reason to disagree.
2. **Scale is bounded by attention, never by turn length.** The cheap tier must
   always be a *valid but suboptimal* policy, and LLM calls must never scale with
   `time_per_tick_minutes`. Anything that breaks this is not polish, it is a
   correctness regression.
3. **Document the non-obvious in code and here.** Kilo has repeatedly
   misread these systems because the comments and docs were thin.

## Now — finish WorldPainter (next 1–2 sessions)

The compiler is the keystone; fog-of-war, zone fidelity and chunk persistence
are all waiting on a world that has been compiled once.

| Task | Why now |
|---|---|
| task-496 grid→graph compiler | Cells become areas + ways in the *existing* formats, so the engine does not change. Region-merge + deterministic templated descriptions keep the lattice LLM-free. |
| task-398 deterministic structure generation | The generator is the only sanctioned way to mint an unmade scope, and it must be reproducible and editable after the fact. |
| task-520 canvas scale (review) | Verify the acceptance: a 16k-cell grid pans/zooms, the route tool reports cells · turns · hours, a route paints in one request with one undo entry. |
| task-397 world scopes | Finish the projection so the editor/runtime can address a zone without inventing a second spatial model. |
| task-400 Pines vertical slice | The end-to-end proof: a painted region compiled, walked, and trusted. Small on purpose. |

**Exit test:** paint a zone, compile it, load only that scope in the graph, walk
it in play, commit it — with no engine change.

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
(task-419), fog of war (task-499), zone-driven fidelity (task-500), elevation
sightlines (task-498), chunk persistence (task-401) and the projection benchmark
(task-402). Characters: canonical character nodes (task-457), id-first identity
(task-446), nicknames (task-447), the life-experience generator (task-404),
structured appearance/personality (task-507).

## Then — UI & tooling

Library browser overhaul (task-510), expression pack (task-512), the help-center
audit (task-521), save/load UX + list perf (task-455/454), Playwright persistence
(task-444), and the trigger-graph overhaul (task-502/388).

## Always-on hygiene

- **Drain review.** 140 tasks sit in review; a dedicated drain session keeps the
  folder honest rather than letting review become a second todo.
- **13 pre-existing JS unit failures** (`test_plan_tracker.js`) — fix or delete
  the stale expectations.
- **Stale tasks** (`task-409`'s action-budget blocker is retired; task-475's
  gaps are recorded in code) must be re-read against the current design before
  acting.

## Risks to watch

- **WorldPainter clobber trap** (task-289/290/317): decide grid-canonical vs
  baked-and-hand-edited *per zone* before compiling, or a re-compile will erase
  hand edits.
- **The review backlog hides real debt.** 140 review tasks is bigger than the
  todo list; if it is not drained, "done" stops meaning done.
- **Performance is not the first proof.** task-400 is deliberately small — do
  not let a vertical slice turn into a million-node benchmark.
