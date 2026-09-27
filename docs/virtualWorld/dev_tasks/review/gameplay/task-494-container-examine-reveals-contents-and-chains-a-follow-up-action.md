---
type: task
status: review
area: gameplay
priority: medium
---

# task-494: Container examine reveals contents and chains a follow-up action

**Filed:** 2026-09-23
**Related:** task-352, task-493, task-430, task-104

## Goal

Make container contents an explicit reveal and allow a two-step single turn: examine <container> marks its contents discovered (they render 'known' and become usable), and the examine can be followed by one item action (take/use) in the same turn, mirroring the dash multi-step precedent (engine/movement.py dash_to_area, tick_manager.py move/dash handling) and governed by action_costs. Decide whether carried-container contents stop being auto-listed before an examine. Belongs with the task-352 action-economy work.

## Measured (2026-09-27) — half the file describes code that does not exist

### 1. The stated precedent is not there. At all.

The Goal points at "the dash multi-step precedent (`engine/movement.py`
`dash_to_area`, `tick_manager.py` move/dash handling)". Measured:

- **`engine/tick_manager.py` has no move/dash multi-step logic.** Its only dash
  mention is a cost-modifier branch, `engine/tick_manager.py:113-138`:
  `if action_name in ("move", "dash"):` — which then walks
  `TraitSystem.get_move_cost_mods`. That is a trait lookup, not a second action.
- **`engine/movement.py:800-831` `dash_to_area` performs exactly one hop**, and
  says so itself. `tests/test_movement.py:131-136` pins it: *"dash_to_area
  performs ONE move — the second hop is a separate chained decision made by the
  agent engine, not part of this call."*

The real precedent is **client-side**, in two places:

- `static/js/agent-engine.js:14-21` — `CHAIN_RULES = { dash: ['go','wait'],
  lead: [...], grab: [...] }`, dispatched at `:731-740` on
  `actionSucceeded`, executed by `_runChainFollowUp` at `:1236-1290`. Validation
  at `:1259-1263` accepts a whitelisted verb **or any exit name**.
- `static/js/agent-engine.js:328-339` — the human "burst" phase, gated on
  `reply.action.startsWith('dash ')` plus a failure regex
  `/locked|blocked|can't|could not|fail/i` over the narration. UI side:
  `static/js/agent/human-turn-composer.js:474`, `:708-709`, `:765`.

**There is no server-side follow-up mechanism to mirror, and no server-side
notion of a turn boundary to enforce one.** Measured, exhaustively negative:

- `Player.reset_turn_state(...)` (`player.py`, called from
  `engine/tick_manager.py:267`) carries nothing about actions.
- No counter, flag or per-turn state on `Player` or `VirtualWorld` of any kind.
  The nearest thing is `VirtualWorld._clock_advanced_by_task`
  (`virtual_world_engine.py:126-130`), written only by `rest`
  (`engine/tick_manager.py:1045`) and read only by `tools/game_tools.py`.
- **`POST /api/action` never advances the clock.** The turn boundary is
  `TurnQueue.endTurn()` → `POST /api/turn/apply` →
  `routes/action_handlers.py:1315-1321` → `world.tick_turn()`. So a chained
  `examine` + `take` is literally two `/api/action` POSTs before one
  `/api/turn/apply`, and **the server cannot tell that apart from two turns'
  worth of actions.** That is task-352's scoping note 6: `routes/` contains zero
  calls to `world.tick` / `advance_clock`.
- The background tier is the opposite model by design —
  `engine/background_simulation.py:8`: *"Every character takes one action per
  turn — the turn is the unit of agency."*

And the direction of travel cuts against building it here: **task-352's
acceptance criteria say `CHAIN_RULES` and the burst phase are to be retired**
in favour of a tier/slot model, and this task file itself says it "belongs with
the task-352 action-economy work". Building a second, server-side chaining
mechanism would be building the thing task-352 is about to delete.

### 2. `action_costs` is a vital-cost mechanism with no slot concept

Two things share the name, and neither can govern a follow-up today:

- The base table `ACTION_COSTS` (`virtual_world_engine.py:109-125`) — move,
  open, close, look, use, take, drop, fumble, fear, interest. **No `examine`, no
  `put`.** Merged in `engine/tick_manager.py:90-150`. Read at exactly one place,
  `engine/tick_manager.py:100`.
- The per-item-node property `action_costs` (`{verb: {vital: amount}}`), read at
  three places: `take_drop_actions.py:524`, `use_actions.py:137`,
  `consume_actions.py:131`.

Both are **purely about vitals**. Neither has a notion of slots, of slots
granted, or of follow-up permission. Note also that `action_costs` is
per-**item** while a follow-up allowance is per-**turn** — putting a turn
semantics on a per-item key is a category error waiting to happen.

### 3. The reveal was already half-built — and the half that was missing is the half that mattered

`engine/items/examine_actions.py:285-311` already un-hides every `hidden` child
and prints one flat line per relation. Two things were wrong with it:

- **The un-hiding is global.** `cn.properties["current_state"] = "normal"` is
  written on the node, once, permanently, in the save. The first character to
  open a chest revealed the loot to *everyone, forever*.
- **The character who looked was never credited.** `_register_item_discovery`
  is called for the container itself (`:241`) and for nothing inside it. So the
  contents never rendered as "known", and a second character who opened the same
  chest later got nothing at all — the reveal had already happened and there was
  no per-player record to add.

"Known" is decided **client-side**, and all three readers read
`player.discovered_items`:

- `static/js/agent/prompt-builder/contextual-actions.js:131-134` `isDiscovered()`
  and `:195` (the `examine` verb bracket is dropped once discovered)
- `static/js/agent/prompt-builder/room-context.js:302, 317, 331`
- `static/js/agent/prompt-builder/memory-context.js:26, 34-35, 177`

No engine renderer change is needed. The stamp is the whole contract.

### 4. "Are carried-container contents auto-listed?" — measured: no, and it is a no-op

Every UI surface reads direct `EDGE_CARRYING` only, with no recursion:

| Surface | file:line |
|---|---|
| `get_inventory` | `engine/items/examine_actions.py:470-479` |
| `scene.you.carrying` | `engine/scene_snapshot.py:283-290` |
| `inventory` command | `routes/action_handlers.py:758-775` |

The only auto-exposure is (a) the examine prose, and (b) **the name matcher**:
`engine/matching.py:299-324` and `engine/player_manager.py:345-355` add every
non-hidden content name to the candidate set, and
`engine/item_reach.py:147-157` walks to arbitrary depth for
`use`/`use_on`/`eat`/`drink`/`place`/`put`/`toggle`. So `take apple` out of a
basket already resolves with no examine having happened.

This is worth being precise about, because the acceptance criterion's wording
("become usable") is half-true: **contents are already usable before the
examine.** Making them *not* usable would mean changing reachability across
`matching.py`, `player_manager.find_item_node` and `item_reach`, and would break
`test_take_from_container_works` and `test_container_contents_are_reachable`
(`tests/test_item_actions.py:190-214`). Recorded as a decision below rather than
done, because the acceptance says contents become usable, not invisible.

## Decisions taken

1. **Ship the reveal, not the chaining.** The reveal is a two-line fix for a
   real, measurable hole with a real user-visible symptom. The chaining needs a
   turn model that does not exist and that task-352 is about to build.
2. **Do not make contents unreachable before an examine.** They were never
   listed, and the acceptance criterion asks for usable, not hidden. Recorded.
3. **Sequence the chaining after task-352**, not in parallel with it. See below.

## Done (2026-09-27) — the reveal

`engine/items/examine_actions.py:302-333`. For every item the examine reports —
`in`, `on`, `under`, `behind`, `beside`, `at`, not just `in` — the character who
looked is now credited via `_register_item_discovery`, which writes the
observation memory and the `discovered_items` entry that all three client-side
readers consult. The global `current_state` un-hide is unchanged; the two are
different things and the file now says so.

Added a `revealed` count so a genuinely new chest says
`Taking in 2 new things.` and a re-look at a known one does not narrate a
discovery. `_register_item_discovery` is idempotent, so the credit is safe to
apply unconditionally on every examine.

`tests/test_item_actions.py` gains `TestExamineMarksContentsDiscovered`, 8
tests: the stamp, the serialised payload the client reads, a second character
getting credit independently, no re-discovery on a second examine, the singular
case, already-visible contents, a locked container revealing nothing, and a
table with things on it (proving it is not `in`-only).

### Re-measured

- `tests/test_item_actions.py` 67 → 75, all passing. No existing test needed
  changing: the reveal line is appended *after* `"Inside you see: …"`, so the
  existing assertions still match.
- 860 tests across `-k "examine or item or container or freshness or observation
  or novelty or inventory or take or drop"`: only the 8 pre-existing
  `test_mcp_*` failures.
- Entertainment is not a problem: `engine/novelty.py:208`
  (`novelty_budget_remaining`) already caps how much a single tick can pay, so a
  chest with ten things in it cannot pay ten novelty bonuses.

## Not done — the chained follow-up, and why, and how

**Not attempted.** This is a new mechanism, not a mirror of one, and the
sequencing matters:

1. **task-352 lands a slot/tier model.** Its acceptance criteria retire
   `CHAIN_RULES` and the human burst. Anything built now on the client-side
   precedent is built on scaffolding that is scheduled for deletion.
2. **Then, and only then, the server needs to know a turn's shape.** Chaining
   only becomes enforceable when the engine — not the browser — knows how many
   actions a turn holds. `POST /api/action` advancing nothing is what makes the
   browser the only thing that currently knows.
3. **Then `examine` grants a follow-up slot**, and `action_costs` is reconsidered
   as a *vital* cost for that slot rather than being given a new slot semantic.
   A per-item key governing a per-turn allowance should not survive the
   redesign.

Suggested landing when task-352 is done: `examine <container>` returns a
"follow-up available" affordance, the client offers exactly one `take`/`use` from
the revealed names, and the engine rejects a second action if the slot is spent.
Reuse whatever slot model task-352 introduces rather than adding a counter next
to it.

## Acceptance

- [x] `examine <container>` marks its contents discovered so they render as
      known. — `TestExamineMarksContentsDiscovered`, 8 tests
- [x] Decided whether carried-container contents stop being auto-listed before an
      examine. — **They were never auto-listed**; recorded in the doc. The
      "usable" half was already true, deliberately left alone.
- [ ] One follow-up item action in the same turn, governed by `action_costs`. —
      **Blocked on task-352.** Measured above; the precedent the Goal names does
      not exist and the alternative is scheduled for deletion.
- [ ] Tests for a chained take/use and for chaining being disallowed. — Same
      blocker.

## Documentation

`docs/virtualWorld/Items & Inventory/Items Overview.md` §"Container Items" gained
"Examining a container reveals *and* credits its contents (task-494)": the
node-global vs per-player distinction in a table, which three client-side readers
consume `discovered_items`, the `in`-not-only scope, and the reachability point
that contents are targetable before any examine.
