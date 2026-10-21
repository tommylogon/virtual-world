# Plan reconciliation: the `todo` cards under id 600

*Measured 2026-10-20 against `master` at `04f4d315`, by reading the cards, the
newer cards that name them, and the code they cite. This is a **plan-level**
reading: not "is the card still true" but "does newer completed work change
*how* this card should be done, and does the card still stand as a distinct
piece of the overall work".*

## The set, and how it was counted

**40 cards at HEAD, 37 now.** The original count of 41 was wrong by one in
each direction and the error is worth recording:

- `task-491` (action-verb single source of truth) is in `todo/` at HEAD and
  was missing from the 41. It was moved to `review/` by a session before this
  one, and that move is legitimate - the card's own `## Reconnaissance
  (2026-10-02) - NOT started, enumerated` enumerates the scope without
  starting it. It is not part of this set.
- `bug-517` (AI room narration) is in `review/` at HEAD. A subagent moved it
  to `todo/` and then to `inprogress/` during this pass; both moves were
  reversed, because its own verdict is STILL_VALID but that does not make it
  todo - it was already in review, where a card that is not started but is
  actively being looked at belongs.

So: **40 cards at HEAD**, of which 3 closed during this pass (task-405,
task-544, bug-548), leaving **37**.

---

## The short answer

**All 40 cards still hold.** Newer completed work implements *parts* of them;
it does not change their approach, and it does not absorb them. **Zero cards
need a rewrite.** Two needed a *scope narrowing*, and both had already been
narrowed in their own bodies before this pass - the audit confirmed the
narrowing is present and correct rather than proposing it.

Three cards had their **planned surface or premise changed** by newer work, and
each of those is now recorded in the card itself under a `## Plan position
(2026-10-20)` section: **task-99** (the grid hierarchy was inverted by
WorldPainter), **task-580** (task-592 ruled out the scope-row Generate button
it planned to use), and **bug-526** (tab scoping shipped, two things still
open).

The repo already has the vocabulary for this, and it is used consistently:
newer cards say **"Amends: task-409 §4"** (task-417, task-423) rather than
silently replacing. A card that a newer card amends keeps its identity; the
amendment is written down. That is the pattern in every case below.

**The one structural finding.** No newer card has invalidated an older card's
*premise*. The three cards where newer work touches the same machinery all say
so explicitly, and all three keep the older card alive:

- task-317 (done) says of task-290: *"variants + override tracking,
  `template_ref` migration (task-290) - **not started**"*.
- task-827 (review) says of task-299: *"Do not introduce physical mail,
  distance, devices, or voice-call mechanics"* - that is task-827 narrowing
  *itself*, not task-299.
- task-588 (review) says of task-569/570: *"the two consumers this is meant to
  unblock must keep working whichever way it lands"*.

**The most valuable finding is that the plan is already self-maintaining.**
The two cards that looked most at risk of having gone stale are the two that
had already been narrowed by an earlier pass, with a dated `## Current scope`
section saying so. The card bodies are not drifting away from the newer work -
they are being updated *because* of it.

---

## The two cards that were re-narrowed, and the state they are in

### task-409 - background schedules, work and coarse social

**Narrowed, and the narrowing is already in the card.** Two things landed that
move the work:

1. **The planner is gone.** The card's own `## Current scope (2026-10-15)`
   says it: *"The old deterministic 'goal-directed planner' in this card is
   superseded by the MOSIAC/GIMP design and tasks 702/704. Keep the work here
   on the existing calendar schedule and the still-missing capped background
   reflection. Do not build another planner or selector."* MOSIAC is the
   decision layer; task-701 (plan templates), task-702 (plan executor) and
   task-704 (MOSIAC selector) own plan selection and execution. task-409 must
   not build a second one.
2. **The arithmetic behind the blocker changed.** The card's central open
   question was a three-way design decision (more actions per day / coarser
   need service / drop the working day). Its own 2026-09-24 note supersedes the
   premise of that decision: the 96-actions-per-day figure came from the
   retired action-credit model, and *"the fix is (b), and it is decided:
   background characters use bundled tasks authored as data."*

The *social* half was amended into two newer cards, both done: **task-417**
(*"Amends: task-409 §4"*, the co-presence gate) and **task-423** (*"Amends:
task-409 §4 - this is the mature form of coarse meetings"*).

**State: correct.** The `## What` names only the surviving scope (re-measure
the authored schedule data under the current model, decide whether to ship it,
land the capped reflection), the `## Why` says the 2026-09 tables are
historical only, the `## Acceptance` is six items all about the surviving
scope, and an `## Ownership and runtime boundaries` section says explicitly
*"Task 704 owns selecting/binding a suitable plan; task 702 owns executing that
plan. This task must not add a parallel goal planner, action executor, clock,
or character-private store."* No rewrite needed.

### task-414 - batch time advance and non-blocking human

**Narrowed, and the narrowing is already in the card.** The behaviour the card
wanted landed under other ids: **task-436** (durations), **task-464** (timeskip
actions - and it says *"Extend the task-414 endpoint rather than adding a
second transport"*), **task-466** (attended plan continuation), **task-481**
(per-character soak orders). What did **not** land is the named route:
`rg -n "world/advance"` returns zero code hits; only `/api/world/timeskip` and
`/api/world/soak` are registered.

**State: correct.** The card carries a per-ask table with six rows, five
marked *done* against the task that delivered them and one marked *missing*
(the named route). The `## How` gives two options - add the route, or close
the ask by documenting `/api/world/timeskip` as canonical - and the
`## Acceptance` has four items, all about the missing route. No rewrite
needed. The one open decision is a naming question, not a scope question.

---

## Cards whose approach is intact, with the newer work that touches them

These are the cards a reader should check first, because the newer work
sits right next to them.

| Card | Newer work | What it actually did | Effect on the older card |
|---|---|---|---|
| **task-290** template variants | task-317 (done) | bidirectional template link + sync | **Holds.** task-317 lists task-290's scope as *"not started"* and its own card defers to task-290. task-290 also has `template_ref` and overrides groundwork already in `engine/sync.py`. |
| **task-467** belief travel | task-499 (done) fog of war, task-495 (review) grids | per-agent `known` set, grid substrate | **Holds.** task-499 implements the *reveal* half that task-467's acceptance depends on; task-467 still owns belief-resolution and the heading budget. |
| **task-401** chunk persistence | task-581/582/583/584 (review), task-439 (review), task-500 (done) | stable area ids, load/unload APIs, global scope index | **Holds as an umbrella.** Four sub-cards split the scope and are all in review. task-439 says *"task-401 is the real remaining dependent"*; task-500 says *"task-401 already owns chunk load/evict"*. The umbrella should close when the four land, not before. |
| **task-402** world-scale benchmark | task-855 (review), task-572 (review) | focused runtime state, E2E harness | **Holds.** task-572 explicitly says *"Not done here: task-402's >=100k-node synthetic generator"* - the benchmark is still owed, and task-572 is the harness it grows from. |
| **task-299** long-distance comms | task-493 (done) device model, task-491 (review) verb registry | parts-as-child-items, no `power` property | **Holds.** task-493 is the *substrate* task-299's design was rewritten around (*"the device assembled from items model agreed in the task-299 discussion"*). task-299 still owns the `comms_channel` and the call/answer mechanic. |
| **task-437** turn order | task-465 (done) the dial, task-533 (done) simultaneous pipeline, task-481 (done) | UI mode dropdown, simultaneous world-turn pipeline | **Holds, but narrower.** The *ordering* is still client-side (`turn-queue.ts` still switches on `config.turnOrder`) and `turn_order` is still dead data. task-533 fixed the pipeline, not the order; task-465 is the dial only. The card's own note says the client-side resolution is *"to be replaced by reading the server's list"*. |
| **task-592** outline hierarchy | task-627 (done) | flat select to `<optgroup>` nesting | **Holds.** Different surface - task-627 fixed the picker, task-592 owns the tree fold (world to scope to area) that has not landed. |
| **task-570** hostile distribution | task-571/573/588 (review) | biome affinity, coverage lint, vocabulary investigation | **Holds.** task-588 is an investigation whose answer must not change what task-570 does (*"must keep working whichever way it lands"*). The real blocker is content: **2** hostile-tagged library entries exist (`anne.json`, a child, and `shadow_pelt.json`, a worg) - not the *zero* the card claimed. |
| **task-570** vs task-588 | - | - | **Correction made.** The card said *zero* entries tagged predator/bandit/monster/hostile. Measured: 2 (`anne.json` tagged `monster` but also `child`; `shadow_pelt.json` tagged `predator`, `worg`, `animal`, `pack`). Two further raw matches are not character definitions - an item-level `"tag": "hostile"` and a `"hostile": true` property. The card's conclusion (unusable content) stands; its count was wrong. |
| **task-404** life experience | task-843 (done) Persona import, task-427 (done) | LLM to Persona schema, creature lineages | **Holds.** task-427 says explicitly *"task-404 is life experiences, not species"* - the boundary is drawn, not crossed. task-843 is a different surface (Persona import vs authored life events). |
| **task-332** legacy effect props | task-23/97/177 (done) | `locked_with` and `locked` consolidation | **Holds.** The same pattern continues: those three consolidated the *locked* boolean, and `effect_stat`/`effect_amount`/`effect_target` is the next one in the same family. 535 data matches, 23 engine reads. |
| **task-594** swimming | task-745 (review) river biomes, task-769/776/852/855 (review) | river biome family, hazards, map/graph coords | **Holds.** task-745 added the terrain and a 7-hazard table whose `rapids.on_fail` declares `suffocating` - the right carrier for an air vital. No `swim` verb, no `Air` vital (16 vitals, none named Air). |
| **task-591** structures authoring | task-716 (review) | fisherman vertical slice | **Holds.** `static/js/structures.ts` exists but its capture entry point is dead code - the live right-click handler has no `save_structure` case. `data/library/structures/` does not exist. |
| **task-580** unmade-scope Generate | task-585 (review) | regenerate overwrites a hand edit | **Holds.** task-585 lists *"The `Generate` button and preview surface (task-580)"* as still open - it depends on it, not the reverse. |
| **task-99** room grids | task-419 (done), task-320/330/518 (review) | relational spatial model, scry, ranged weapons | **Holds, with a boundary.** task-419 says *"Room grids / intra-area coordinates (task-99) - explicitly not this model"*. task-99 is the intra-area half and nothing else has taken it. |
| **task-414** (again) | task-436/464 (done) | see above | narrow. |
| **task-482** timeskip follow-ups | task-670 (review) | one-human timeskip soaks the cast | **Holds.** Long spans landed (`MAX_MINUTES` is 10,080, not 1,440). Vendor leisure buying and explore-prefers-frontier are still open; the string "vendor" does not occur anywhere in `engine/timeskip.py`. |

---

## Cards with no newer work bearing on them

These are untouched by anything completed since they were filed. They hold on
their own merits and their own evidence.

`task-384` (per-edit undo feed - the live feed exists for external/MCP edits
via `world_changed`, but the per-edit undo for in-app edits does not),
`task-435` (offline generators still mint way prose - 5 tools still write it),
`task-441` (frontend giants - `worldpainter/editor.ts` grew 3,927 to **5,002**),
`task-455` / `task-456` (save/load dialog UX and split - 4 native dialogs still
in `saveload-view.ts`; `renderSaveRow` does not exist),
`task-509` / `task-510` (library batch triggers and browser overhaul - the
items pane is still `width:800px` against 2,208 items),
`task-477` (combat on the central check system - `checks.resolve` has 2
callers, neither in combat; `combat.py` and `grapple.py` roll their own),
`bug-517`, `bug-519`, `bug-526`, `bug-536`, `bug-538`, `bug-539`, `bug-540`,
`bug-547`, `bug-553`, `bug-554`, `bug-555`, `bug-556`, `bug-557`.

---

## The three cards that were closed

Verified independently, not taken on the subagent's word:

- **task-405** (LLM raw inspector) - `static/js/ui/llm-inspector.ts` is
  registered at `templates/index.html:1405`; 4 capture call sites in
  `llm-client.ts`; the `llm_raw_exchanges` IndexedDB store; the `showRawLLM`
  opt-in. The planned `static/css/llm-inspector.css` was never created - the
  card now says so.
- **task-544** (soak space-time view) - `static/js/soak/soak-spacetime.ts`
  (34,566 bytes) wired at `soak-ui.ts:1326`; 62 unit tests pass
  (`tools/unit/test_soak_spacetime.js`). The `Soak Lab.md` feature page still
  said "in progress" with a list of remaining work that the tests now cover;
  it has been corrected.
- **bug-548** (scenario name) - `static/js/ui/scenario-status.ts:41-48` writes
  `#scenario-name-text` on refresh.

---

## What still needs doing, in plan order

Nothing here needs a rewrite. The open work, in the order the plan implies:

1. **task-414** - settle the naming question: add
   `POST /api/world/advance {ticks: N}`, or document `/api/world/timeskip` as
   canonical and delete the named-route acceptance item. Everything else the
   card asked for is already delivered.
2. **task-409** - re-measure the authored schedule data under the current
   timeframe-and-flow model and decide whether to ship it, then land the
   capped daily reflection. Both are already correctly scoped in the card.
3. **task-570** - the content blocker is now measured accurately (2 entries,
   not 0). The card body is corrected; the work itself is authoring
   predator/bandit definitions.
4. **task-401** - stays open as an umbrella until task-581/582/583/584 land.
   It should not be re-litigated.
5. Everything else: hold, with the evidence recorded in the card.

---

## Notes on method

- Every "still holds" claim is anchored to a file:line or a count measured on
  2026-10-20. Where a claim was checked and found wrong, the card was
  corrected: task-570's character count, and task-544's stale feature page.
- Two subagent claims were rejected on verification: "0 hits for `belief` in
  engine/" (11 hits, in `engine/memory_dynamics.py`) and "combat uses the
  central check system" (2 callers, neither in combat).
- `python tools/tasks.py validate` reports **0 errors**. Five duplicate-id card
  pairs were removed after confirming in each pair that the `review/` copy was
  strictly more advanced (all acceptance boxes checked against unchecked,
  later commit, same filename). Four card moves that a `git stash` had
  reverted were restored.
